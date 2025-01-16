import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from puzzlehunt.models import Hunt, Puzzle, Team
from datetime import timedelta
import os

User = get_user_model()

pytestmark = pytest.mark.django_db

@pytest.fixture
def setup_database():
    """Run initial setup and return the created hunt"""
    # Set domain environment variable
    os.environ['DOMAIN'] = 'example.com'
    
    # Simulate answering 'yes' to the setup prompt
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr('builtins.input', lambda: 'yes')
        call_command('initial_setup')
    
    return Hunt.objects.get(is_current_hunt=True)

@pytest.fixture
def setup_puzzles(setup_database):
    """Create a set of test puzzles with a specific configuration"""
    hunt = setup_database
    
    # Create test puzzles
    puzzles = []
    for i in range(1, 4):
        puzzle = Puzzle.objects.create(
            hunt=hunt,
            name=f"Test Puzzle {i}",
            answer=f"ANSWER{i}",
            order_number=i,
            id=f"{i}"
        )
        puzzles.append(puzzle)
    
    # Set up hunt configuration
    config = """
    # P1 unlocks at start
    P1 <= 0 POINTS
    # P2 unlocks after solving P1
    P2 <= P1
    # P3 unlocks after solving P1 and getting 10 points
    P3 <= (P1 AND 10 POINTS)
    # Solving P1 gives 5 points
    5 POINTS <= P1
    # Solving P2 gives 5 points
    5 POINTS <= P2
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()
    
    return hunt, puzzles

@pytest.fixture
def normal_user():
    """Create a non-staff user"""
    return User.objects.create_user(
        email="hunter@example.com",
        password="testpass123",
        display_name="Test Hunter"
    )

def test_hunt_experience(client, setup_puzzles, normal_user):
    """
    Test the complete hunt experience from start to finish
    """
    hunt, puzzles = setup_puzzles
    
    # Test 1: Unauthenticated user access
    response = client.get(reverse('puzzlehunt:index'))
    assert response.status_code == 200
    
    # Verify hunt page requires login
    response = client.get(reverse('puzzlehunt:hunt_view', args=[hunt.id]))
    assert response.status_code == 302  # Redirect to login
    
    # Test 2: Login and initial access
    client.login(email="hunter@example.com", password="testpass123")
    response = client.get(reverse('puzzlehunt:index'))
    assert response.status_code == 200
    assert hunt.name in response.content.decode()
    
    # Test 3: Create and join team
    response = client.post(reverse('puzzlehunt:team_create'), {
        'name': 'Test Team',
        'is_local': True
    })
    assert response.status_code == 302
    team = Team.objects.get(name='Test Team')
    assert normal_user in team.members.all()
    
    # Test 4: Access hunt page
    response = client.get(reverse('puzzlehunt:hunt_view', args=[hunt.id]))
    assert response.status_code == 200
    
    # Test 5: Verify initial puzzle access
    team.process_unlocks()  # Process initial unlocks
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"
    
    # Test 6: Solve first puzzle
    puzzle1 = puzzles[0]
    response = client.post(reverse('puzzlehunt:puzzle_submit', args=[puzzle1.id]), {
        'answer': 'ANSWER1'
    })
    assert response.status_code == 200
    team.process_unlocks()
    
    # Test 7: Verify puzzle unlocks after solving
    team.refresh_from_db()
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2  # P1 and P2 should be unlocked
    assert team.points == 5  # Should have earned 5 points
    
    # Test 8: Solve second puzzle
    puzzle2 = puzzles[1]
    response = client.post(reverse('puzzlehunt:puzzle_submit', args=[puzzle2.id]), {
        'answer': 'ANSWER2'
    })
    assert response.status_code == 200
    team.process_unlocks()
    # Test 9: Verify final state
    team.refresh_from_db()
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3  # All puzzles should be unlocked
    assert team.points == 10  # Should have 10 total points