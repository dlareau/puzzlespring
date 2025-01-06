from abc import ABC, abstractmethod
from typing import Any, Dict, List
from django.forms import ValidationError
from huey.contrib.djhuey import task
import requests
from .models import Event, NotificationPlatform, NotificationSubscription
import logging

logger = logging.getLogger(__name__)


class NotificationHandler(ABC):
    """Base class for platform-specific notification handlers"""

    # Add handler mapping as a class variable
    handlers = {
        NotificationPlatform.PlatformType.DISCORD: 'DiscordHandler',
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
        self.config = platform.config

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
    @abstractmethod
    def get_required_config_keys(cls) -> List[str]:
        """Return list of required keys for platform configuration"""
        pass


class DiscordHandler(NotificationHandler):
    """Handler for Discord webhook notifications"""

    @classmethod
    def get_required_config_keys(cls) -> List[str]:
        return ['webhook_url']

    def validate_destination(self, destination: str) -> None:
        if not (destination and destination.startswith('https://discord.com/api/webhooks/')):
            raise ValidationError('Invalid Discord webhook URL')

    def send_notification(self, subscription: NotificationSubscription, event: Event) -> bool:
        try:
            webhook_url = subscription.destination
            message = self._format_event_message(event)
            
            response = requests.post(webhook_url, json={
                "content": message
            })
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def _format_event_message(self, event: Event) -> str:
        """Format event data into a Discord message"""
        return f"**{event.get_type_display()}**: {event.notification_text}"


@task()
def send_event_notifications(event_id: int):
    """Huey task to send notifications for an event"""
    try:
        # Get event object
        event = Event.objects.get(pk=event_id)

        # Get all active subscriptions that match this event type
        subscriptions = NotificationSubscription.objects.filter(
            active=True,
            event_types__contains=event.type
        )

        # Filter by hunt if specified
        hunt_subs = subscriptions.filter(hunt=event.hunt)
        general_subs = subscriptions.filter(hunt__isnull=True)
        subscriptions = hunt_subs | general_subs

        # If event is team-specific, filter subscriptions to only team members
        if event.team:
            subscriptions = subscriptions.filter(user__in=event.team.members.all())

        # Send notifications using centralized handler mapping
        for subscription in subscriptions:
            handler = NotificationHandler.create_handler(subscription.platform)
            if handler:
                handler.send_notification(subscription, event)

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
    except Exception as e:
        logger.error(f"Error sending notifications for event {event_id}: {e}")