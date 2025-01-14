import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

from puzzlehunt.models import DisplayOnlyHunt

pytestmark = pytest.mark.django_db

def test_index_view(client, basic_hunt):
    """Test the index view displays the current hunt correctly"""
    url = reverse('puzzlehunt:index')
    now = timezone.now()
    
    # Initial state - current hunt
    basic_hunt.start_date = now + timedelta(days=1)
    basic_hunt.end_date = now + timedelta(days=2)
    basic_hunt.display_start_date = now + timedelta(days=1)
    basic_hunt.display_end_date = now + timedelta(days=2)
    basic_hunt.save()
    
    response = client.get(url)
    assert response.status_code == 200
    
    # Convert UTC dates to America/New_York for comparison
    start_date = basic_hunt.display_start_date.astimezone(ZoneInfo('America/New_York'))
    end_date = basic_hunt.display_end_date.astimezone(ZoneInfo('America/New_York'))
    
    # Check that the current hunt is displayed
    assert basic_hunt.name in response.content.decode()
    assert start_date.strftime("%m/%d/%y") in response.content.decode()
    assert end_date.strftime("%m/%d/%y") in response.content.decode()
    
    # Test different hunt states
    # Test locked state (more than 2 days before start)
    basic_hunt.start_date = now + timedelta(days=3)
    basic_hunt.end_date = now + timedelta(days=4)
    basic_hunt.display_start_date = now + timedelta(days=3)
    basic_hunt.display_end_date = now + timedelta(days=4)
    basic_hunt.save()
    response = client.get(url)
    assert "Our next hunt" in response.content.decode()
    
    # Test public state (after end date)
    basic_hunt.start_date = now - timedelta(days=2)
    basic_hunt.end_date = now - timedelta(days=1)
    basic_hunt.display_start_date = now - timedelta(days=2)
    basic_hunt.display_end_date = now - timedelta(days=1)
    basic_hunt.save()
    response = client.get(url)
    assert "Our previous hunt" in response.content.decode()
    
    # Test day of hunt state (between start and end)
    basic_hunt.start_date = now - timedelta(hours=1)
    basic_hunt.end_date = now + timedelta(hours=1)
    basic_hunt.display_start_date = now - timedelta(hours=1)
    basic_hunt.display_end_date = now + timedelta(hours=1)
    basic_hunt.save()
    response = client.get(url)
    assert "Our current hunt" in response.content.decode()

def test_archive_view(client, basic_hunt):
    """Test the archive view displays hunts correctly"""
    url = reverse('puzzlehunt:archive')
    now = timezone.now()
    
    # Create a display only hunt for testing
    display_hunt = DisplayOnlyHunt.objects.create(
        name="Old Hunt",
        display_start_date=now - timedelta(days=365),
        display_end_date=now - timedelta(days=364),
        num_teams=10,
        num_puzzles=10
    )
    
    # Make the regular hunt public by setting end date in the past
    basic_hunt.start_date = now - timedelta(days=2)
    basic_hunt.end_date = now - timedelta(days=1)
    basic_hunt.display_start_date = now - timedelta(days=2)
    basic_hunt.display_end_date = now - timedelta(days=1)
    basic_hunt.save()
    
    response = client.get(url)
    assert response.status_code == 200
    
    # Convert UTC dates to America/New_York for comparison
    start_date = basic_hunt.display_start_date.astimezone(ZoneInfo('America/New_York'))
    display_start_date = display_hunt.display_start_date.astimezone(ZoneInfo('America/New_York'))
    
    # Check both hunts are displayed
    content = response.content.decode()
    assert basic_hunt.name in content
    assert display_hunt.name in content
    
    # Check dates are displayed
    assert start_date.strftime("%m/%d/%y") in content
    assert display_start_date.strftime("%m/%d/%y") in content
    
    # Check non-public hunts are not displayed (by setting end date in future)
    basic_hunt.start_date = now
    basic_hunt.end_date = now + timedelta(days=1)
    basic_hunt.display_start_date = now
    basic_hunt.display_end_date = now + timedelta(days=1)
    basic_hunt.save()
    response = client.get(url)
    assert basic_hunt.name not in response.content.decode()
    assert display_hunt.name in response.content.decode()

def test_user_detail_view(client, basic_user):
    """Test the user detail view functions correctly"""
    url = reverse('puzzlehunt:user_detail_view')
    
    # Test unauthenticated access
    response = client.get(url)
    assert response.status_code == 302  # Should redirect to login
    
    # Test authenticated access
    client.force_login(basic_user)
    response = client.get(url)
    assert response.status_code == 200
    assert "User Details" in response.content.decode()
    
    # Test user update
    new_first_name = "Updated"
    response = client.patch(url, data={'first_name': new_first_name})
    assert response.status_code == 302  # Should redirect after successful update
    
    # Test HTMX update
    response = client.patch(url, data={'first_name': new_first_name}, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    assert "User details changed successfully" in response.content.decode()
