import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone

from puzzlehunt.models import (
    NotificationPlatform, NotificationSubscription, Event, Team, Puzzle,
    PuzzleStatus, Hint, User
)
from puzzlehunt.notifications import (
    BrowserHandler, NotificationHandler,
    send_event_notifications, EmailHandler, WebhookHandler
)
from puzzlehunt.utils import PuzzlehuntChannelManager

pytestmark = pytest.mark.django_db


class TestChannelManager:
    """Tests for PuzzlehuntChannelManager user channel support"""

    def test_user_can_access_own_channel(self, basic_user):
        """Test that users can access their own user channel"""
        cm = PuzzlehuntChannelManager()
        assert cm.can_read_channel(basic_user, f'user-{basic_user.pk}') is True

    def test_user_cannot_access_other_user_channel(self, basic_user, staff_user):
        """Test that users cannot access other users' channels"""
        cm = PuzzlehuntChannelManager()
        assert cm.can_read_channel(basic_user, f'user-{staff_user.pk}') is False

    def test_unauthenticated_cannot_access_user_channel(self, basic_user):
        """Test that unauthenticated users cannot access user channels"""
        cm = PuzzlehuntChannelManager()
        assert cm.can_read_channel(None, f'user-{basic_user.pk}') is False

    def test_staff_channel_access(self, staff_user, basic_user):
        """Test staff channel access is restricted to staff users"""
        cm = PuzzlehuntChannelManager()
        assert cm.can_read_channel(staff_user, 'staff') is True
        assert cm.can_read_channel(basic_user, 'staff') is False

    def test_invalid_user_channel_format(self, basic_user):
        """Test that invalid user channel formats are rejected"""
        cm = PuzzlehuntChannelManager()
        assert cm.can_read_channel(basic_user, 'user-invalid') is False
        assert cm.can_read_channel(basic_user, 'user-') is False


class TestBrowserHandler:
    """Tests for BrowserHandler notification handler"""

    def test_browser_handler_in_handlers_mapping(self):
        """Test that BrowserHandler is registered in handlers mapping"""
        assert NotificationPlatform.PlatformType.BROWSER in NotificationHandler.handlers
        assert NotificationHandler.handlers[NotificationPlatform.PlatformType.BROWSER] == 'BrowserHandler'

    def test_browser_handler_validate_config(self):
        """Test that BrowserHandler requires no config"""
        # Should not raise any exception
        BrowserHandler.validate_config({})
        BrowserHandler.validate_config(None)

    def test_browser_handler_validate_destination(self):
        """Test that BrowserHandler accepts any destination"""
        platform = NotificationPlatform(type=NotificationPlatform.PlatformType.BROWSER)
        handler = BrowserHandler(platform)
        # Should not raise any exception
        handler.validate_destination('')
        handler.validate_destination(None)
        handler.validate_destination('anything')

    @patch('puzzlehunt.notifications.send_event')
    def test_browser_handler_sends_sse_notification(self, mock_send_event, basic_user, basic_hunt):
        """Test that BrowserHandler sends SSE notifications correctly"""
        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.BROWSER,
            name='Test Browser',
            enabled=True
        )
        handler = BrowserHandler(platform)

        # Create a mock event with notification text
        team = Team.objects.create(
            name='Test Team',
            hunt=basic_hunt
        )
        puzzle = Puzzle.objects.create(
            id='TEST01',
            name='Test Puzzle',
            hunt=basic_hunt,
            order_number=1,
            answer='ANSWER'
        )
        PuzzleStatus.objects.create(
            team=team,
            puzzle=puzzle,
            unlock_time=timezone.now()
        )
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        mock_send_event.assert_called_once()
        call_args = mock_send_event.call_args
        assert call_args[0][0] == f'user-{basic_user.pk}'
        assert call_args[0][1] == 'notification'
        assert 'bulmaToast.toast' in call_args[0][2]


class TestHintRefundEvent:
    """Tests for HINT_REFUND event type"""

    def test_hint_refund_event_type_exists(self):
        """Test that HINT_REFUND event type is defined"""
        assert hasattr(Event.EventType, 'HINT_REFUND')
        assert Event.EventType.HINT_REFUND == 'HREF'

    def test_hint_refund_in_queue_types(self):
        """Test that HINT_REFUND is in queue_types"""
        assert Event.EventType.HINT_REFUND in Event.queue_types

    def test_hint_refund_in_public_types(self):
        """Test that HINT_REFUND is in public_types"""
        assert Event.EventType.HINT_REFUND in Event.public_types

    @patch('puzzlehunt.notifications.send_event_notifications')
    def test_hint_refund_creates_event(self, mock_send, basic_hunt, basic_user):
        """Test that refunding a hint creates a HINT_REFUND event"""
        team = Team.objects.create(name='Test Team', hunt=basic_hunt, num_available_hints=1)
        team.members.add(basic_user)
        puzzle = Puzzle.objects.create(
            id='TEST01', name='Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        status = PuzzleStatus.objects.create(
            team=team, puzzle=puzzle, unlock_time=timezone.now() - timezone.timedelta(hours=2)
        )
        hint = Hint.objects.create(
            team=team, puzzle=puzzle,
            request='Help please',
            request_time=timezone.now(),
            last_modified_time=timezone.now()
        )

        # Refresh to get updated values
        team.refresh_from_db()

        # Now refund the hint
        hint.refund()

        # Check that HINT_REFUND event was created
        refund_event = Event.objects.filter(type=Event.EventType.HINT_REFUND).first()
        assert refund_event is not None
        assert refund_event.team == team
        assert refund_event.puzzle == puzzle


class TestBrowserSubscriptionAutoCreation:
    """Tests for automatic browser subscription creation"""

    def test_new_user_gets_browser_subscription(self, basic_hunt):
        """Test that new users automatically get a browser subscription"""
        browser_platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.BROWSER,
            name='Browser Notifications',
            enabled=True
        )

        # Create a new user
        user = User.objects.create_user(
            email='newuser@example.com',
            password='testpass123'
        )

        # Check that browser subscription was created
        subscription = NotificationSubscription.objects.filter(
            user=user,
            platform=browser_platform
        ).first()

        assert subscription is not None
        assert subscription.active is True
        assert Event.EventType.PUZZLE_SOLVE in subscription.event_types_list
        assert Event.EventType.PUZZLE_UNLOCK in subscription.event_types_list
        assert Event.EventType.HINT_RESPONSE in subscription.event_types_list
        assert Event.EventType.HINT_REFUND in subscription.event_types_list

    def test_no_subscription_if_no_browser_platform(self):
        """Test that no subscription is created if browser platform doesn't exist"""
        # Ensure no browser platform exists
        NotificationPlatform.objects.filter(
            type=NotificationPlatform.PlatformType.BROWSER
        ).delete()

        # Create a new user
        user = User.objects.create_user(
            email='newuser2@example.com',
            password='testpass123'
        )

        # Check that no browser subscription was created
        subscription = NotificationSubscription.objects.filter(
            user=user,
            platform__type=NotificationPlatform.PlatformType.BROWSER
        ).first()

        assert subscription is None


class TestBrowserNotificationOptOut:
    """Tests for browser notification opt-out behavior"""

    @patch('puzzlehunt.notifications.send_event')
    def test_browser_notifications_sent_to_subscribed_users(self, mock_send_event, basic_hunt):
        """Test that browser notifications are sent to users with active subscriptions"""
        browser_platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.BROWSER,
            name='Browser Notifications',
            enabled=True
        )

        # Create user with subscription (simulating auto-creation)
        user = User.objects.create_user(email='test@example.com', password='testpass')
        NotificationSubscription.objects.create(
            user=user,
            platform=browser_platform,
            event_types=Event.EventType.PUZZLE_UNLOCK,
            active=True
        )

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        team.members.add(user)
        puzzle = Puzzle.objects.create(
            id='TEST01', name='Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(
            team=team, puzzle=puzzle, unlock_time=timezone.now()
        )

        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        # Clear any previous calls
        mock_send_event.reset_mock()

        # Call the task directly (not as a Huey task)
        send_event_notifications.call_local(event.pk)

        # Should have sent notification
        assert mock_send_event.called
        # Check it was sent to the correct user channel
        call_args = [call[0] for call in mock_send_event.call_args_list]
        user_channel_calls = [args for args in call_args if args[0] == f'user-{user.pk}']
        assert len(user_channel_calls) > 0

    @patch('puzzlehunt.notifications.send_event')
    def test_browser_notifications_respect_opt_out(self, mock_send_event, basic_hunt):
        """Test that opted-out users don't receive browser notifications"""
        browser_platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.BROWSER,
            name='Browser Notifications',
            enabled=True
        )

        # Create user (auto-creates browser subscription)
        user = User.objects.create_user(email='optout@example.com', password='testpass')

        # Set the auto-created subscription to inactive (opt out)
        subscription = NotificationSubscription.objects.get(
            user=user,
            platform=browser_platform
        )
        subscription.active = False
        subscription.save()

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        team.members.add(user)
        puzzle = Puzzle.objects.create(
            id='TEST02', name='Test Puzzle 2', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(
            team=team, puzzle=puzzle, unlock_time=timezone.now()
        )

        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).last()

        # Clear any previous calls from PuzzleStatus creation
        mock_send_event.reset_mock()

        # Call the task directly
        send_event_notifications.call_local(event.pk)

        # Check that no notification was sent to this user's channel
        call_args = [call[0] for call in mock_send_event.call_args_list]
        user_channel_calls = [args for args in call_args if args[0] == f'user-{user.pk}']
        assert len(user_channel_calls) == 0

    @patch('puzzlehunt.notifications.send_event')
    def test_multi_user_team_selective_notifications(self, mock_send_event, basic_hunt):
        """Test that notifications are sent selectively based on user subscriptions"""
        browser_platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.BROWSER,
            name='Browser Notifications',
            enabled=True
        )

        # Create two users (both auto-get browser subscriptions)
        user_active = User.objects.create_user(email='active@example.com', password='testpass')
        user_inactive = User.objects.create_user(email='inactive@example.com', password='testpass')

        # user_active keeps default active subscription
        # Set user_inactive's subscription to inactive (opt out)
        subscription = NotificationSubscription.objects.get(
            user=user_inactive,
            platform=browser_platform
        )
        subscription.active = False
        subscription.save()

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        team.members.add(user_active, user_inactive)
        puzzle = Puzzle.objects.create(
            id='TEST03', name='Test Puzzle 3', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(
            team=team, puzzle=puzzle, unlock_time=timezone.now()
        )

        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).last()

        # Clear any previous calls
        mock_send_event.reset_mock()

        # Call the task directly
        send_event_notifications.call_local(event.pk)

        # Gather all calls to user channels
        call_args = [call[0] for call in mock_send_event.call_args_list]
        active_user_calls = [args for args in call_args if args[0] == f'user-{user_active.pk}']
        inactive_user_calls = [args for args in call_args if args[0] == f'user-{user_inactive.pk}']

        # Active user should receive notification
        assert len(active_user_calls) > 0
        # Inactive user should NOT receive notification
        assert len(inactive_user_calls) == 0


class TestHintResponseRelatedData:
    """Tests for hint response related_data distinction"""

    @patch('puzzlehunt.notifications.send_event_notifications')
    def test_hint_response_initial_has_response_data(self, mock_send, basic_hunt, basic_user, staff_user):
        """Test that initial hint response has 'response' related_data"""
        team = Team.objects.create(name='Test Team', hunt=basic_hunt, num_available_hints=1)
        team.members.add(basic_user)
        puzzle = Puzzle.objects.create(
            id='TEST03', name='Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(
            team=team, puzzle=puzzle, unlock_time=timezone.now() - timezone.timedelta(hours=2)
        )
        hint = Hint.objects.create(
            team=team, puzzle=puzzle,
            request='Help please',
            request_time=timezone.now(),
            last_modified_time=timezone.now()
        )

        hint.respond(staff_user, 'Here is your hint')

        response_event = Event.objects.filter(type=Event.EventType.HINT_RESPONSE).first()
        assert response_event is not None
        assert response_event.related_data == 'response'

    @patch('puzzlehunt.notifications.send_event_notifications')
    def test_hint_response_update_has_response_update_data(self, mock_send, basic_hunt, basic_user, staff_user):
        """Test that updated hint response has 'response_update' related_data"""
        team = Team.objects.create(name='Test Team', hunt=basic_hunt, num_available_hints=1)
        team.members.add(basic_user)
        puzzle = Puzzle.objects.create(
            id='TEST04', name='Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(
            team=team, puzzle=puzzle, unlock_time=timezone.now() - timezone.timedelta(hours=2)
        )
        hint = Hint.objects.create(
            team=team, puzzle=puzzle,
            request='Help please',
            request_time=timezone.now(),
            last_modified_time=timezone.now()
        )

        # First response
        hint.respond(staff_user, 'Here is your hint')
        # Update response
        hint.respond(staff_user, 'Updated hint text')

        response_events = Event.objects.filter(type=Event.EventType.HINT_RESPONSE).order_by('timestamp')
        assert response_events.count() == 2
        assert response_events[0].related_data == 'response'
        assert response_events[1].related_data == 'response_update'


class TestEmailHandler:
    """Tests for EmailHandler notification handler"""

    def test_email_handler_in_handlers_mapping(self):
        """Test that EmailHandler is registered in handlers mapping"""
        assert NotificationPlatform.PlatformType.EMAIL in NotificationHandler.handlers
        assert NotificationHandler.handlers[NotificationPlatform.PlatformType.EMAIL] == 'EmailHandler'

    def test_email_handler_validate_config_valid(self):
        """Test that EmailHandler accepts valid config with from_email"""
        # Should not raise
        EmailHandler.validate_config({'from_email': 'noreply@example.com'})

    def test_email_handler_validate_config_invalid(self):
        """Test that EmailHandler rejects config without from_email"""
        from django.forms import ValidationError

        with pytest.raises(ValidationError):
            EmailHandler.validate_config({})
        with pytest.raises(ValidationError):
            EmailHandler.validate_config(None)

    def test_email_handler_validate_destination_valid(self):
        """Test that EmailHandler accepts valid email addresses"""
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.EMAIL,
            config={'from_email': 'noreply@example.com'}
        )
        handler = EmailHandler(platform)
        # Should not raise any exception
        handler.validate_destination('user@example.com')
        handler.validate_destination('test.user+tag@subdomain.example.org')

    def test_email_handler_validate_destination_invalid(self):
        """Test that EmailHandler rejects invalid email addresses"""
        from django.forms import ValidationError
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.EMAIL,
            config={'from_email': 'noreply@example.com'}
        )
        handler = EmailHandler(platform)

        with pytest.raises(ValidationError):
            handler.validate_destination('not-an-email')
        with pytest.raises(ValidationError):
            handler.validate_destination('')
        with pytest.raises(ValidationError):
            handler.validate_destination('missing@domain')

    @patch('django.core.mail.send_mail')
    def test_email_handler_sends_notification(self, mock_send_mail, basic_hunt, basic_user):
        """Test that EmailHandler sends notifications correctly"""
        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.EMAIL,
            name='Test Email',
            enabled=True,
            config={'from_email': 'noreply@puzzlehunt.com'}
        )
        handler = EmailHandler(platform)

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        puzzle = Puzzle.objects.create(
            id='MAIL01', name='Email Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(team=team, puzzle=puzzle, unlock_time=timezone.now())
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            destination='recipient@example.com',
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args[1]
        assert call_kwargs['from_email'] == 'noreply@puzzlehunt.com'
        assert call_kwargs['recipient_list'] == ['recipient@example.com']
        assert '[PuzzleSpring]' in call_kwargs['subject']


class TestWebhookHandler:
    """Tests for WebhookHandler notification handler"""

    def test_webhook_handler_in_handlers_mapping(self):
        """Test that WebhookHandler is registered in handlers mapping"""
        assert NotificationPlatform.PlatformType.WEBHOOK in NotificationHandler.handlers
        assert NotificationHandler.handlers[NotificationPlatform.PlatformType.WEBHOOK] == 'WebhookHandler'

    def test_webhook_handler_validate_config_requires_format(self):
        """Test that WebhookHandler requires format in config"""
        from django.forms import ValidationError

        with pytest.raises(ValidationError):
            WebhookHandler.validate_config({})
        with pytest.raises(ValidationError):
            WebhookHandler.validate_config(None)

    def test_webhook_handler_validate_config_valid_formats(self):
        """Test that WebhookHandler accepts valid format values"""
        # Should not raise
        WebhookHandler.validate_config({'format': 'slack'})
        WebhookHandler.validate_config({'format': 'discord'})
        WebhookHandler.validate_config({'format': 'generic'})
        WebhookHandler.validate_config({'format': 'telegram', 'bot_token': 'test-token'})

    def test_webhook_handler_validate_config_invalid_format(self):
        """Test that WebhookHandler rejects invalid format values"""
        from django.forms import ValidationError

        with pytest.raises(ValidationError):
            WebhookHandler.validate_config({'format': 'invalid'})

    def test_webhook_handler_validate_config_telegram_requires_token(self):
        """Test that telegram format requires bot_token"""
        from django.forms import ValidationError

        with pytest.raises(ValidationError):
            WebhookHandler.validate_config({'format': 'telegram'})
        # Should not raise with token
        WebhookHandler.validate_config({'format': 'telegram', 'bot_token': 'test'})

    def test_webhook_handler_validate_config_custom_destination_regex(self):
        """Test that WebhookHandler validates custom destination_regex"""
        from django.forms import ValidationError

        # Valid regex should work
        WebhookHandler.validate_config({'format': 'generic', 'destination_regex': r'^https://custom\.domain/'})

        # Invalid regex should fail
        with pytest.raises(ValidationError):
            WebhookHandler.validate_config({'format': 'generic', 'destination_regex': r'[invalid'})


class TestWebhookHandlerSlackFormat:
    """Tests for WebhookHandler with Slack format"""

    def test_slack_format_validate_destination_valid(self):
        """Test that Slack format accepts valid Slack webhook URLs"""
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'slack'}
        )
        handler = WebhookHandler(platform)
        # Should not raise any exception
        handler.validate_destination('https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX')

    def test_slack_format_validate_destination_invalid(self):
        """Test that Slack format rejects invalid URLs"""
        from django.forms import ValidationError
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'slack'}
        )
        handler = WebhookHandler(platform)

        with pytest.raises(ValidationError):
            handler.validate_destination('https://example.com/webhook')
        with pytest.raises(ValidationError):
            handler.validate_destination('')
        with pytest.raises(ValidationError):
            handler.validate_destination(None)

    @patch('puzzlehunt.notifications.requests.post')
    def test_slack_format_sends_notification(self, mock_post, basic_hunt, basic_user):
        """Test that Slack format sends notifications correctly"""
        mock_post.return_value.raise_for_status = MagicMock()

        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            name='Test Slack',
            enabled=True,
            config={'format': 'slack'}
        )
        handler = WebhookHandler(platform)

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        puzzle = Puzzle.objects.create(
            id='SLCK01', name='Slack Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(team=team, puzzle=puzzle, unlock_time=timezone.now())
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            destination='https://hooks.slack.com/services/T00000000/B00000000/XXXXX',
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == subscription.destination
        assert 'text' in call_args[1]['json']
        # Check Slack message format (uses asterisks for bold)
        assert '*' in call_args[1]['json']['text']


class TestWebhookHandlerDiscordFormat:
    """Tests for WebhookHandler with Discord format"""

    def test_discord_format_validate_destination_valid(self):
        """Test that Discord format accepts valid Discord webhook URLs"""
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'discord'}
        )
        handler = WebhookHandler(platform)
        # Should not raise any exception
        handler.validate_destination('https://discord.com/api/webhooks/123456789/XXXXXXXX')

    def test_discord_format_validate_destination_invalid(self):
        """Test that Discord format rejects invalid URLs"""
        from django.forms import ValidationError
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'discord'}
        )
        handler = WebhookHandler(platform)

        with pytest.raises(ValidationError):
            handler.validate_destination('https://example.com/webhook')
        with pytest.raises(ValidationError):
            handler.validate_destination('')

    @patch('puzzlehunt.notifications.requests.post')
    def test_discord_format_sends_notification(self, mock_post, basic_hunt, basic_user):
        """Test that Discord format sends notifications correctly"""
        mock_post.return_value.raise_for_status = MagicMock()

        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            name='Test Discord',
            enabled=True,
            config={'format': 'discord'}
        )
        handler = WebhookHandler(platform)

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        puzzle = Puzzle.objects.create(
            id='DISC01', name='Discord Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(team=team, puzzle=puzzle, unlock_time=timezone.now())
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            destination='https://discord.com/api/webhooks/123456789/XXXXXXXX',
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == subscription.destination
        assert 'content' in call_args[1]['json']
        # Check Discord message format (uses double asterisks for bold)
        assert '**' in call_args[1]['json']['content']


class TestWebhookHandlerTelegramFormat:
    """Tests for WebhookHandler with Telegram format"""

    def test_telegram_format_validate_destination_valid(self):
        """Test that Telegram format accepts valid chat IDs and usernames"""
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'telegram', 'bot_token': 'test-token'}
        )
        handler = WebhookHandler(platform)
        # Should not raise any exception
        handler.validate_destination('123456789')  # Numeric chat ID
        handler.validate_destination('-100123456789')  # Group/channel ID (negative)
        handler.validate_destination('@username')  # Username

    def test_telegram_format_validate_destination_invalid(self):
        """Test that Telegram format rejects invalid destinations"""
        from django.forms import ValidationError
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'telegram', 'bot_token': 'test-token'}
        )
        handler = WebhookHandler(platform)

        with pytest.raises(ValidationError):
            handler.validate_destination('')
        with pytest.raises(ValidationError):
            handler.validate_destination(None)
        with pytest.raises(ValidationError):
            handler.validate_destination('not-valid')

    @patch('puzzlehunt.notifications.requests.post')
    def test_telegram_format_sends_notification(self, mock_post, basic_hunt, basic_user):
        """Test that Telegram format sends notifications correctly"""
        mock_post.return_value.raise_for_status = MagicMock()

        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            name='Test Telegram',
            enabled=True,
            config={'format': 'telegram', 'bot_token': 'test-bot-token-123'}
        )
        handler = WebhookHandler(platform)

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        puzzle = Puzzle.objects.create(
            id='TGRM01', name='Telegram Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(team=team, puzzle=puzzle, unlock_time=timezone.now())
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            destination='123456789',
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'test-bot-token-123' in call_args[0][0]
        assert call_args[1]['json']['chat_id'] == '123456789'
        assert call_args[1]['json']['parse_mode'] == 'Markdown'


class TestWebhookHandlerGenericFormat:
    """Tests for WebhookHandler with generic format"""

    def test_generic_format_validate_destination_valid(self):
        """Test that generic format accepts valid HTTPS URLs"""
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'generic'}
        )
        handler = WebhookHandler(platform)
        # Should not raise any exception
        handler.validate_destination('https://example.com/webhook')
        handler.validate_destination('https://api.myapp.io/notifications/puzzlehunt')

    def test_generic_format_validate_destination_invalid(self):
        """Test that generic format rejects non-HTTPS URLs"""
        from django.forms import ValidationError
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'generic'}
        )
        handler = WebhookHandler(platform)

        with pytest.raises(ValidationError):
            handler.validate_destination('http://example.com/webhook')  # HTTP not allowed
        with pytest.raises(ValidationError):
            handler.validate_destination('')
        with pytest.raises(ValidationError):
            handler.validate_destination(None)

    @patch('puzzlehunt.notifications.requests.post')
    def test_generic_format_sends_notification(self, mock_post, basic_hunt, basic_user):
        """Test that generic format sends notifications correctly"""
        mock_post.return_value.raise_for_status = MagicMock()

        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            name='Test Webhook',
            enabled=True,
            config={'format': 'generic'}
        )
        handler = WebhookHandler(platform)

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        puzzle = Puzzle.objects.create(
            id='WHBK01', name='Webhook Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(team=team, puzzle=puzzle, unlock_time=timezone.now())
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            destination='https://example.com/webhook',
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://example.com/webhook'
        payload = call_args[1]['json']
        assert 'event_type' in payload
        assert 'event_type_display' in payload
        assert 'notification_text' in payload
        assert 'timestamp' in payload
        assert 'hunt_id' in payload
        assert 'puzzle_id' in payload
        assert 'team_id' in payload


class TestWebhookHandlerCustomOverrides:
    """Tests for WebhookHandler with custom config overrides"""

    def test_custom_destination_regex_override(self):
        """Test that custom destination_regex overrides default"""
        platform = NotificationPlatform(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            config={'format': 'generic', 'destination_regex': r'^https://custom\.domain/'}
        )
        handler = WebhookHandler(platform)

        # Should accept custom domain
        handler.validate_destination('https://custom.domain/webhook')

        # Should reject other domains
        from django.forms import ValidationError
        with pytest.raises(ValidationError):
            handler.validate_destination('https://example.com/webhook')

    @patch('puzzlehunt.notifications.requests.post')
    def test_custom_payload_key_override(self, mock_post, basic_hunt, basic_user):
        """Test that custom payload_key overrides default"""
        mock_post.return_value.raise_for_status = MagicMock()

        platform = NotificationPlatform.objects.create(
            type=NotificationPlatform.PlatformType.WEBHOOK,
            name='Test Custom Webhook',
            enabled=True,
            config={'format': 'slack', 'payload_key': 'message'}
        )
        handler = WebhookHandler(platform)

        team = Team.objects.create(name='Test Team', hunt=basic_hunt)
        puzzle = Puzzle.objects.create(
            id='CUST01', name='Custom Test Puzzle', hunt=basic_hunt,
            order_number=1, answer='ANSWER'
        )
        PuzzleStatus.objects.create(team=team, puzzle=puzzle, unlock_time=timezone.now())
        event = Event.objects.filter(type=Event.EventType.PUZZLE_UNLOCK).first()

        subscription = NotificationSubscription(
            user=basic_user,
            platform=platform,
            destination='https://hooks.slack.com/services/T00000000/B00000000/XXXXX',
            event_types=Event.EventType.PUZZLE_UNLOCK
        )

        result = handler.send_notification(subscription, event)

        assert result is True
        call_args = mock_post.call_args
        # Custom payload_key should be used instead of default 'text'
        assert 'message' in call_args[1]['json']
        assert 'text' not in call_args[1]['json']


class TestHandlerRegistryConsolidated:
    """Tests verifying that only the consolidated handlers are registered"""

    def test_only_three_handlers_registered(self):
        """Test that only BROWSER, EMAIL, and WEBHOOK handlers are registered"""
        assert len(NotificationHandler.handlers) == 3
        assert set(NotificationHandler.handlers.keys()) == {
            NotificationPlatform.PlatformType.BROWSER,
            NotificationPlatform.PlatformType.EMAIL,
            NotificationPlatform.PlatformType.WEBHOOK,
        }

    def test_platform_types_match_handlers(self):
        """Test that PlatformType choices match handler registry"""
        platform_types = set(NotificationPlatform.PlatformType.values)
        handler_types = set(NotificationHandler.handlers.keys())
        assert platform_types == handler_types
