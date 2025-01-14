import pytest
from django.urls import reverse
from puzzlehunt.models import Team, User

pytestmark = pytest.mark.django_db

def test_team_create_view_success(client, basic_hunt, basic_user):
    """Test successful team creation through the view"""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_create')
    
    response = client.post(url, {
        'name': 'View Test Team',
        'is_local': True
    })
    assert response.status_code == 302  # Redirect after success
    
    team = Team.objects.first()
    assert team.name == 'View Test Team'
    assert team.is_local is True
    assert team.hunt == basic_hunt
    assert team.members.first() == basic_user

def test_team_create_view_duplicate_name(client, basic_hunt, basic_user):
    """Test team creation fails with duplicate name"""
    Team.objects.create(
        name="Existing Team",
        hunt=basic_hunt
    )
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_create')
    
    response = client.post(url, {
        'name': 'Existing Team',
        'is_local': True
    })
    assert response.status_code == 200  # Returns to form with errors
    assert Team.objects.count() == 1  # No new team created
    assert 'name' in response.context['form'].errors

def test_team_create_view_invalid_name(client, basic_hunt, basic_user):
    """Test team creation fails with invalid name (no alphanumeric characters)"""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_create')
    
    response = client.post(url, {
        'name': '!@#$%',
        'is_local': True
    })
    assert response.status_code == 200  # Returns to form with errors
    assert Team.objects.count() == 0
    assert 'name' in response.context['form'].errors

def test_team_update_view_success(client, basic_hunt, basic_user):
    """Test successful team update through the view with HTMX"""
    team = Team.objects.create(
        name="Original Name",
        hunt=basic_hunt
    )
    team.members.add(basic_user)
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_update', kwargs={'pk': team.pk})
    
    response = client.post(url, {
        'name': 'Updated Via View',
        'is_local': True
    }, HTTP_HX_REQUEST='true')
    
    assert response.status_code == 200
    team.refresh_from_db()
    assert team.name == 'Updated Via View'
    assert team.is_local is True
    assert team.hunt == basic_hunt  # Hunt remains unchanged

def test_team_update_view_duplicate_name(client, basic_hunt, basic_user):
    """Test team update fails with duplicate name"""
    Team.objects.create(
        name="Existing Team",
        hunt=basic_hunt
    )
    team = Team.objects.create(
        name="Original Name",
        hunt=basic_hunt
    )
    team.members.add(basic_user)
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_update', kwargs={'pk': team.pk})
    
    response = client.post(url, {
        'name': 'Existing Team',
        'is_local': True
    }, HTTP_HX_REQUEST='true')
    
    assert response.status_code == 200
    team.refresh_from_db()
    assert team.name == "Original Name"  # Name remains unchanged
    assert 'name' in response.context['form'].errors

def test_team_update_view_unauthorized(client, basic_hunt, basic_user):
    """Test that only team members can update the team"""
    other_user = User.objects.create_user(
        email="other@example.com",
        password="testpass123"
    )
    team = Team.objects.create(
        name="Original Name",
        hunt=basic_hunt
    )
    team.members.add(other_user)
    
    client.force_login(basic_user)  # Login as non-team member
    url = reverse('puzzlehunt:team_update', kwargs={'pk': team.pk})
    
    response = client.post(url, {
        'name': 'Should Not Update',
        'is_local': True
    })
    
    assert response.status_code == 403
    team.refresh_from_db()
    assert team.name == "Original Name" 

def test_team_join_with_code(client, basic_hunt, basic_user):
    """Test joining a team using a join code"""
    team = Team.objects.create(
        name="Team to Join",
        hunt=basic_hunt
    )
    join_code = team.join_code
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_join_current')
    
    response = client.get(url, {'code': join_code})
    assert response.status_code == 302  # Redirect after success
    
    team.refresh_from_db()
    assert basic_user in team.members.all()

def test_team_join_with_invalid_code(client, basic_hunt, basic_user):
    """Test joining a team with an invalid join code"""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_join_current')
    
    response = client.get(url, {'code': 'INVALID'})
    assert response.status_code == 200  # Returns to form with error
    assert 'errors' in response.context
    assert Team.objects.count() == 0

def test_team_join_with_link(client, basic_hunt, basic_user):
    """Test joining a team using a direct link with join code"""
    team = Team.objects.create(
        name="Team to Join",
        hunt=basic_hunt
    )
    join_code = team.join_code
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_join', kwargs={'pk': team.pk})
    
    response = client.get(url, {'code': join_code})
    assert response.status_code == 302  # Redirect after success
    
    team.refresh_from_db()
    assert basic_user in team.members.all()

def test_team_join_with_wrong_code(client, basic_hunt, basic_user):
    """Test joining a team with wrong join code in direct link"""
    team = Team.objects.create(
        name="Team to Join",
        hunt=basic_hunt
    )
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_join', kwargs={'pk': team.pk})
    
    response = client.get(url, {'code': 'WRONGCODE'})
    assert response.status_code == 403  # Permission denied
    
    team.refresh_from_db()
    assert basic_user not in team.members.all()

def test_team_join_already_in_team(client, basic_hunt, basic_user):
    """Test joining a team when already in another team for the hunt"""
    # Create and join first team
    first_team = Team.objects.create(
        name="First Team",
        hunt=basic_hunt
    )
    first_team.members.add(basic_user)
    
    # Try to join second team
    second_team = Team.objects.create(
        name="Second Team",
        hunt=basic_hunt
    )
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_join', kwargs={'pk': second_team.pk})
    
    response = client.get(url, {'code': second_team.join_code})
    assert response.status_code == 302  # Redirects back to current team
    
    first_team.refresh_from_db()
    second_team.refresh_from_db()
    assert basic_user in first_team.members.all()
    assert basic_user not in second_team.members.all()

def test_team_leave(client, basic_hunt, basic_user):
    """Test leaving a team while other members remain"""
    # Create another user to keep the team alive
    other_user = User.objects.create_user(
        email="other@example.com",
        password="testpass123"
    )
    
    team = Team.objects.create(
        name="Team to Leave",
        hunt=basic_hunt
    )
    team.members.add(basic_user)
    team.members.add(other_user)
    team_id = team.id
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_leave', kwargs={'pk': team.pk})
    
    response = client.post(url)
    assert response.status_code == 302  # Redirect after success
    
    team.refresh_from_db()
    assert basic_user not in team.members.all()
    assert other_user in team.members.all()  # Other user still in team
    assert Team.objects.filter(id=team_id).exists()  # Team still exists

def test_team_leave_last_member(client, basic_hunt, basic_user):
    """Test team is deleted when last member leaves"""
    team = Team.objects.create(
        name="Team to Delete",
        hunt=basic_hunt
    )
    team.members.add(basic_user)
    team_id = team.id
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_leave', kwargs={'pk': team.pk})
    
    response = client.post(url)
    assert response.status_code == 302  # Redirect after success
    
    # Team should be deleted
    assert not Team.objects.filter(id=team_id).exists()

def test_team_leave_unauthorized(client, basic_hunt, basic_user):
    """Test that non-members cannot leave a team"""
    team = Team.objects.create(
        name="Team to Not Leave",
        hunt=basic_hunt
    )
    
    client.force_login(basic_user)
    url = reverse('puzzlehunt:team_leave', kwargs={'pk': team.pk})
    
    response = client.post(url)
    assert response.status_code == 403  # Permission denied 