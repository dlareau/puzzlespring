from abc import ABC, abstractmethod
import re
from django.db.models import Q
from django.forms import ValidationError
from django_eventstream import send_event
from huey.contrib.djhuey import task
import json
import requests
from .models import Event, NotificationPlatform, NotificationSubscription
import logging

logger = logging.getLogger(__name__)


class NotificationHandler(ABC):
    """Base class for platform-specific notification handlers"""

    # Add handler mapping as a class variable
    handlers = {
        NotificationPlatform.PlatformType.BROWSER: 'BrowserHandler',
        NotificationPlatform.PlatformType.EMAIL: 'EmailHandler',
        NotificationPlatform.PlatformType.WEBHOOK: 'WebhookHandler',
    }

    @classmethod
    def get_handler(cls, platform_type):
        """Get the appropriate handler class for a platform type"""
        handler_name = cls.handlers.get(platform_type)
        if handler_name:
            # Get the handler class from the current module
            return globals()[handler_name]
        return None

    @classmethod
    def create_handler(cls, platform: NotificationPlatform):
        """Create an instance of the appropriate handler for a platform"""
        handler_class = cls.get_handler(platform.type)
        if handler_class:
            return handler_class(platform)
        return None

    def __init__(self, platform: NotificationPlatform):
        self.platform = platform
        self.config = platform.config or {}

    @abstractmethod
    def validate_destination(self, destination: str) -> None:
        """
        Validate platform-specific destination.
        Raises ValidationError if destination is invalid.
        """
        pass

    @abstractmethod
    def send_notification(self, subscription: NotificationSubscription, event: Event) -> bool:
        """
        Send a notification for an event to a specific subscription.
        Returns True if successful, False otherwise.
        """
        pass

    @classmethod
    def validate_config(cls, config: dict) -> None:
        """Validate platform config. Override in subclasses. Raises ValidationError if invalid."""
        pass  # Default: no validation needed


class BrowserHandler(NotificationHandler):
    """Handler for browser SSE notifications"""

    @classmethod
    def validate_config(cls, config: dict) -> None:
        pass  # No config required

    def validate_destination(self, destination: str) -> None:
        pass

    def send_notification(self, subscription: NotificationSubscription, event: Event) -> bool:
        try:
            user = subscription.user
            text = event.notification_text
            if not text:
                return False

            escaped_text = json.dumps(text)
            toast_data = f"{{message: {escaped_text}, position: 'bottom-right', appendTo: document.getElementById('sse-message-container')}}"
            sse_string = f"<script> bulmaToast.toast({toast_data});</script>"
            send_event(f"user-{user.pk}", "notification", sse_string, json_encode=False)
            return True
        except Exception as e:
            logger.error(f"Failed to send browser notification: {e}")
            return False


class EmailHandler(NotificationHandler):
    """Handler for email notifications"""

    @classmethod
    def validate_config(cls, config: dict) -> None:
        if not config or 'from_email' not in config:
            raise ValidationError("Email config must include 'from_email'")

    def validate_destination(self, destination: str) -> None:
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_email(destination)
        except DjangoValidationError:
            raise ValidationError('Invalid email address')

    def send_notification(self, subscription: NotificationSubscription, event: Event) -> bool:
        from django.core.mail import send_mail
        try:
            send_mail(
                subject=f"[PuzzleSpring] {event.get_type_display()}",
                message=event.notification_text,
                from_email=self.config['from_email'],
                recipient_list=[subscription.destination],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class WebhookHandler(NotificationHandler):
    """Handler for webhook notifications (Discord, Slack, Telegram, generic)

    All formats are configured via FORMAT_DEFAULTS with these keys:
    - destination_regex: Regex to validate the  user supplied destination field
    - url_template: URL template with {destination}, {bot_token}, etc. placeholders
    - payload_key: Key for message in payload (None = send full event JSON)
    - message_format: Format string for message with {type} and {text} placeholders
    - destination_payload_key: If set, adds destination to payload under this key
    - extra_payload: Additional fields to merge into payload
    - required_config: List of required config keys for this format
    """

    FORMAT_DEFAULTS = {
        'slack': {
            'destination_regex': r'^https://hooks\.slack\.com/',
            'url_template': '{destination}',
            'payload_key': 'text',
            'message_format': '*{type}*: {text}',
        },
        'discord': {
            'destination_regex': r'^https://discord\.com/api/webhooks/',
            'url_template': '{destination}',
            'payload_key': 'content',
            'message_format': '**{type}**: {text}',
        },
        'telegram': {
            'destination_regex': r'^(@[\w]+|[-]?\d+)$',
            'url_template': 'https://api.telegram.org/bot{bot_token}/sendMessage',
            'payload_key': 'text',
            'message_format': '*{type}*: {text}',
            'destination_payload_key': 'chat_id',
            'extra_payload': {'parse_mode': 'Markdown'},
            'required_config': ['bot_token'],
        },
        'generic': {
            'destination_regex': r'^https://',
            'url_template': '{destination}',
            # No payload_key means full event JSON is sent
        },
    }

    @classmethod
    def validate_config(cls, config: dict) -> None:
        if not config or 'format' not in config:
            raise ValidationError("Webhook config must include 'format'")

        fmt = config['format']
        if fmt not in cls.FORMAT_DEFAULTS:
            raise ValidationError(f"Invalid format: {fmt}. Must be one of: {', '.join(cls.FORMAT_DEFAULTS.keys())}")

        defaults = cls.FORMAT_DEFAULTS[fmt]

        # Check required config keys
        for key in defaults.get('required_config', []):
            if key not in config:
                raise ValidationError(f"{fmt} format requires '{key}' in config")

        # Validate destination_regex override is valid regex if provided
        if 'destination_regex' in config:
            try:
                re.compile(config['destination_regex'])
            except re.error as e:
                raise ValidationError(f"Invalid destination_regex: {e}")

    def _get_setting(self, key, default=None):
        """Get a setting from config, falling back to format defaults."""
        fmt = self.config.get('format', 'generic')
        defaults = self.FORMAT_DEFAULTS.get(fmt, {})
        return self.config.get(key, defaults.get(key, default))

    def validate_destination(self, destination: str) -> None:
        pattern = self._get_setting('destination_regex')
        if not pattern:
            return
        if not (destination and re.match(pattern, destination)):
            fmt = self.config.get('format', 'generic')
            raise ValidationError(f'Invalid destination for {fmt} format')

    def send_notification(self, subscription: NotificationSubscription, event: Event) -> bool:
        fmt = self.config.get('format', 'generic')

        try:
            # Build URL from template
            url_template = self._get_setting('url_template', '{destination}')
            url = url_template.format(destination=subscription.destination, **self.config)

            # Build payload
            payload_key = self._get_setting('payload_key')
            if payload_key:
                # Message-based payload
                msg_format = self._get_setting('message_format', '{type}: {text}')
                message = msg_format.format(type=event.get_type_display(), text=event.notification_text)
                payload = {payload_key: message}

                # Add destination to payload if configured
                dest_key = self._get_setting('destination_payload_key')
                if dest_key:
                    payload[dest_key] = subscription.destination

                # Merge extra payload fields
                extra = self._get_setting('extra_payload', {})
                payload.update(extra)
            else:
                # Generic format - send full event JSON
                payload = {
                    "event_type": event.type,
                    "event_type_display": event.get_type_display(),
                    "notification_text": event.notification_text,
                    "timestamp": event.timestamp.isoformat(),
                    "hunt_id": event.hunt_id,
                    "puzzle_id": event.puzzle_id,
                    "team_id": event.team_id,
                }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send {fmt} notification: {e}")
            return False


@task()
def send_event_notifications(event_id: int):
    """Huey task to send notifications for an event"""
    try:
        event = Event.objects.get(pk=event_id)

        # Get all active subscriptions that match this event type
        subscriptions = NotificationSubscription.objects.filter(
            active=True,
            event_types__contains=event.type,
            platform__enabled=True
        )

        # Filter by hunt (hunt-specific OR global subscriptions)
        subscriptions = subscriptions.filter(
            Q(hunt=event.hunt) | Q(hunt__isnull=True)
        )

        # If event is team-specific, filter to team members only
        if event.team:
            subscriptions = subscriptions.filter(user__in=event.team.members.all())

        # Send notifications through appropriate handlers
        for subscription in subscriptions:
            handler = NotificationHandler.create_handler(subscription.platform)
            if handler:
                handler.send_notification(subscription, event)

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
    except Exception as e:
        logger.error(f"Error sending notifications for event {event_id}: {e}")
