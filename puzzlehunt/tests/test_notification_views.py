import pytest
from django.urls import reverse
from django.contrib.messages import get_messages
from puzzlehunt.models import NotificationPlatform, NotificationSubscription, Event

pytestmark = pytest.mark.django_db

@pytest.fixture
def notification_platform():
    """A basic Discord notification platform fixture."""
    return NotificationPlatform.objects.create(
        type=NotificationPlatform.PlatformType.DISCORD,
        name="Test Discord",
        enabled=True,
        config={'webhook_url': 'https://discord.com/api/webhooks/test'}
    )

@pytest.fixture
def notification_subscription(basic_user, notification_platform, basic_hunt):
    """A basic notification subscription fixture."""
    return NotificationSubscription.objects.create(
        user=basic_user,
        platform=notification_platform,
        hunt=basic_hunt,
        event_types=f"{Event.EventType.PUZZLE_SOLVE},{Event.EventType.PUZZLE_UNLOCK}",
        destination="https://discord.com/api/webhooks/test",
        active=True
    )

def test_notification_view_get_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    url = reverse('puzzlehunt:notification_view')
    response = client.get(url)
    assert response.status_code == 302
    assert '/accounts/login/' in response.url

def test_notification_view_get(client, basic_user, notification_subscription):
    """Test that authenticated users can view their notification settings."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_view')
    response = client.get(url)
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'subscriptions' in response.context
    assert list(response.context['subscriptions']) == [notification_subscription]

def test_notification_view_post_valid(client, basic_user, notification_platform, basic_hunt):
    """Test creating a new notification subscription with valid data."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_view')
    
    from urllib.parse import urlencode
    data = {
        'platform': notification_platform.id,
        'hunt': basic_hunt.id,
        'event_types': 'PSUB',
        'destination': 'https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz1234567890',
        'active': 'True',
        'Create': 'Create'
    }
    encoded_data = urlencode(data)
    
    # Add HTMX headers to match real request
    headers = {
        'HX-Request': 'true',
        'HX-Current-URL': f'http://testserver{url}'
    }
    
    response = client.post(url, encoded_data, content_type='application/x-www-form-urlencoded', **headers)
    assert response.status_code == 200
    
    subscription = NotificationSubscription.objects.get(
        user=basic_user,
        platform=notification_platform,
        hunt=basic_hunt
    )
    assert subscription.event_types == 'PSUB'
    assert subscription.destination == 'https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz1234567890'
    assert subscription.active is True
    
    # Verify success message
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "successfully" in str(messages[0])

def test_notification_view_post_invalid(client, basic_user, notification_platform):
    """Test creating a notification subscription with invalid data."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_view')
    
    from urllib.parse import urlencode
    data = {
        'platform': notification_platform.id,
        'event_types': 'PSUB',
        'destination': 'not-a-valid-webhook-url',
        'active': 'True',
        'Create': 'Create'
    }
    encoded_data = urlencode(data)
    
    headers = {
        'HX-Request': 'true',
        'HX-Current-URL': f'http://testserver{url}'
    }
    
    response = client.post(url, encoded_data, content_type='application/x-www-form-urlencoded', **headers)
    assert response.status_code == 200
    assert not NotificationSubscription.objects.filter(user=basic_user).exists()
    assert 'form' in response.context
    assert response.context['form'].errors

def test_notification_delete_success(client, basic_user, notification_subscription):
    """Test deleting a notification subscription."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_delete', args=[notification_subscription.pk])
    
    response = client.delete(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    assert not NotificationSubscription.objects.filter(pk=notification_subscription.pk).exists()
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "deleted" in str(messages[0])

def test_notification_delete_unauthorized(client, notification_subscription):
    """Test that users can't delete other users' subscriptions."""
    url = reverse('puzzlehunt:notification_delete', args=[notification_subscription.pk])
    response = client.delete(url)
    assert response.status_code == 302
    assert NotificationSubscription.objects.filter(pk=notification_subscription.pk).exists()

def test_notification_toggle_success(client, basic_user, notification_subscription):
    """Test toggling a notification subscription's active status."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_toggle', args=[notification_subscription.pk])
    initial_active = notification_subscription.active
    
    response = client.post(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    notification_subscription.refresh_from_db()
    assert notification_subscription.active != initial_active

def test_notification_toggle_unauthorized(client, notification_subscription):
    """Test that users can't toggle other users' subscriptions."""
    url = reverse('puzzlehunt:notification_toggle', args=[notification_subscription.pk])
    response = client.post(url)
    assert response.status_code == 302
    notification_subscription.refresh_from_db()
    assert notification_subscription.active  # Should remain unchanged

def test_notification_view_htmx(client, basic_user, notification_subscription):
    """Test that HTMX requests return partial templates."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_view')
    response = client.get(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    assert 'notification_detail.html' not in [t.name for t in response.templates]
    assert 'partials/_notification_table_and_form.html' in [t.name for t in response.templates]

def test_notification_delete_htmx(client, basic_user, notification_subscription):
    """Test that HTMX delete requests return updated table."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_delete', args=[notification_subscription.pk])
    response = client.delete(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    assert 'notification_table.html' in [t.name for t in response.templates]

def test_notification_toggle_htmx(client, basic_user, notification_subscription):
    """Test that HTMX toggle requests return updated toggle partial."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:notification_toggle', args=[notification_subscription.pk])
    response = client.post(url, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    assert 'partials/_notification_active_toggle.html' in [t.name for t in response.templates]
