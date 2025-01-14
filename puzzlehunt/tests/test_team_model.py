import pytest
from django.utils import timezone
from django.core.exceptions import ValidationError
from puzzlehunt.models import Team, User

pytestmark = pytest.mark.django_db

@pytest.fixture
def basic_team(basic_hunt, basic_user):
    team = Team.objects.create(
        name="Test Team",
        hunt=basic_hunt
    )
    team.members.add(basic_user)
    return team

def test_team_creation(basic_hunt, basic_user):
    """Test basic team creation and validation"""
    team = Team.objects.create(
        name="New Team",
        hunt=basic_hunt
    )
    team.members.add(basic_user)
    
    assert team.name == "New Team"
    assert team.hunt == basic_hunt
    assert team.members.count() == 1
    assert team.members.first() == basic_user

def test_team_size_limit(basic_hunt):
    """Test that teams cannot exceed size limit"""
    team = Team.objects.create(
        name="Size Test Team",
        hunt=basic_hunt
    )
    
    # Add members up to limit
    users = []
    for i in range(basic_hunt.team_size_limit):
        user = User.objects.create_user(
            email=f"user{i}@example.com",
            password="testpass123"
        )
        users.append(user)
        team.members.add(user)
    
    # Try to add one more member
    extra_user = User.objects.create_user(
        email="extra@example.com",
        password="testpass123"
    )
    
    with pytest.raises(ValidationError):
        team.members.add(extra_user)
        team.full_clean()

def test_user_single_team_per_hunt(basic_hunt, basic_user):
    """Test that a user can only be on one team per hunt"""
    team1 = Team.objects.create(
        name="Team 1",
        hunt=basic_hunt
    )
    team1.members.add(basic_user)
    
    team2 = Team.objects.create(
        name="Team 2",
        hunt=basic_hunt
    )
    
    with pytest.raises(ValidationError):
        team2.members.add(basic_user)
        team2.full_clean()

def test_team_status_properties(basic_hunt):
    """Test team status property methods"""
    now = timezone.now()
    future = now + timezone.timedelta(days=1)
    past = now - timezone.timedelta(days=1)

    # Normal team
    normal_team = Team.objects.create(
        name="Normal Team",
        hunt=basic_hunt,
        playtester=False
    )
    assert normal_team.is_normal_team
    assert not normal_team.is_playtester_team
    assert not normal_team.playtest_started
    assert not normal_team.playtest_over
    assert not normal_team.playtest_happening

    # Playtester team - not started
    future_playtest = Team.objects.create(
        name="Future Playtest",
        hunt=basic_hunt,
        playtester=True,
        playtest_start_date=future,
        playtest_end_date=future + timezone.timedelta(days=1)
    )
    assert not future_playtest.is_normal_team
    assert future_playtest.is_playtester_team
    assert not future_playtest.playtest_started
    assert not future_playtest.playtest_over
    assert not future_playtest.playtest_happening

    # Playtester team - currently active
    active_playtest = Team.objects.create(
        name="Active Playtest",
        hunt=basic_hunt,
        playtester=True,
        playtest_start_date=past,
        playtest_end_date=future
    )
    assert not active_playtest.is_normal_team
    assert active_playtest.is_playtester_team
    assert active_playtest.playtest_started
    assert not active_playtest.playtest_over
    assert active_playtest.playtest_happening

    # Playtester team - finished
    finished_playtest = Team.objects.create(
        name="Finished Playtest",
        hunt=basic_hunt,
        playtester=True,
        playtest_start_date=past,
        playtest_end_date=past + timezone.timedelta(hours=1)
    )
    assert not finished_playtest.is_normal_team
    assert finished_playtest.is_playtester_team
    assert finished_playtest.playtest_started
    assert finished_playtest.playtest_over
    assert not finished_playtest.playtest_happening