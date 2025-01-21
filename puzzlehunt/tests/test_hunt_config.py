from unittest.mock import patch
import pytest
from django.utils import timezone
from puzzlehunt.models import Puzzle, Team, PuzzleStatus
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

@pytest.fixture
def hunt_with_puzzles(basic_hunt):
    # Create some puzzles with different order numbers
    puzzles = [
        Puzzle.objects.create(
            hunt=basic_hunt,
            name=f"Puzzle {i}",
            answer="ANSWER",
            order_number=i,
            id=f"{i}"
        ) for i in range(1, 4)
    ]
    return basic_hunt, puzzles

def test_basic_config_parsing(hunt_with_puzzles):
    """Test that a basic valid config can be parsed and saved"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Simple config with one rule
    P1 <= 10 POINTS
    """
    hunt.config = config
    hunt.full_clean()  # Validate before save
    hunt.save()
    assert hunt.config == config

def test_invalid_config_syntax(hunt_with_puzzles):
    """Test that invalid config syntax raises appropriate errors"""
    hunt, puzzles = hunt_with_puzzles
    invalid_config = """
    P1 <= invalid syntax here
    """
    with pytest.raises(ValidationError) as exc_info:
        hunt.config = invalid_config
        hunt.full_clean()  # This should raise the ValidationError
    
    assert 'config' in exc_info.value.message_dict

def test_puzzle_unlock_rules(hunt_with_puzzles):
    """Test that puzzle unlock rules are properly processed"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # P1 unlocks at start
    P1 <= 0 POINTS
    # P2 unlocks after P1 is solved
    P2 <= P1
    # P3 unlocks after 10 points
    P3 <= 10 POINTS
    # Solving P1 gives 5 points
    5 POINTS <= P1
    # Solving P2 gives 5 points
    5 POINTS <= P2
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(
        name="Test Team",
        hunt=hunt
    )
    
    # Process unlocks to get initial state
    team.process_unlocks()
    
    # Test initial state - only P1 should be unlocked
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"

    # Get the existing puzzle status and mark it as solved
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    
    # Process unlocks again to handle the new solve
    team.process_unlocks()
    
    # After solving P1: P2 should unlock and team should have 5 points
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]
    assert team.points == 5

    # Solve P2 to get to 10 points total
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[1])
    status.mark_solved()
    team.process_unlocks()

    # After solving P2: P3 should unlock due to points (10 total)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]
    assert team.points == 10

def test_and_or_rules(hunt_with_puzzles):
    """Test that AND and OR rules work correctly"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # P1 unlocks at start
    P1 <= 0 POINTS
    # P2 unlocks if P1 is solved AND team has 10 points
    P2 <= (P1 AND 10 POINTS)
    # P3 unlocks if P1 is solved OR team has 10 points
    P3 <= (P1 OR 10 POINTS)
    # Give points for solving puzzles
    5 POINTS <= P1
    5 POINTS <= P2
    5 POINTS <= P3
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Initially, only P1 should be unlocked (0 POINTS rule)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"

    # Solve P1 to get 5 points
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()

    # P3 should unlock (OR condition met: P1 solved)
    # P2 should NOT unlock (AND condition not met: P1 solved but only 5 points)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "3"]

    # Solve P3 to get another 5 points
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[2])
    status.mark_solved()
    team.process_unlocks()

    # Now P2 should also unlock (AND condition met: P1 solved AND 10 points)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]


def test_some_of_rule(hunt_with_puzzles):
    """Test that X OF (A, B, C) rules work correctly"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzles unlock with points
    P1 <= 0 POINTS
    P2 <= 0 POINTS
    P3 <= 2 OF (P1, P2, 10 POINTS)
    # Give points for solving puzzles
    5 POINTS <= P1
    10 POINTS <= P2
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Initially P1 and P2 should be unlocked
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Solve P1 to get 5 points (only one condition met: P1 solved)
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()

    # P3 should not unlock yet (only one condition met)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Solve P2 to get another 10 points (now three conditions met: P1 solved, P2 solved, and >10 points)
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[1])
    status.mark_solved()
    team.process_unlocks()

    # P3 should unlock (more than 2 conditions met)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

    # Test with a different team that gets points without solving both puzzles
    team2 = Team.objects.create(name="Test Team 2", hunt=hunt)
    team2.process_unlocks()

    # Solve P2 to get 10 points (two conditions met: P2 solved and 10 points)
    status = PuzzleStatus.objects.get(team=team2, puzzle=puzzles[1])
    status.mark_solved()
    team2.process_unlocks()

    # P3 should unlock (2 conditions met: P2 solved and 10 points)
    unlocked = team2.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

def test_hint_rules(hunt_with_puzzles):
    """Test that hint unlocking rules work correctly"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzle unlocks with points
    P1 <= 0 POINTS
    # Get hints for solving puzzles
    2 HINTS <= P1
    # Get hints every hour
    1 HINT <= EVERY 1 HOUR
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    
    # Process unlocks at start
    team.process_unlocks()
    assert team.num_available_hints == 0

    # Solve P1 to get 2 hints
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()
    assert team.num_available_hints == 2

    # Process after 1 hour
    one_hour = timezone.timedelta(hours=1)
    current_time = timezone.now()
    with patch.object(timezone, 'now', return_value=current_time + one_hour) as mock_now:
        team.process_unlocks()
        assert team.num_available_hints == 3

def test_time_based_unlocks(hunt_with_puzzles):
    """Test that time-based unlock rules work correctly"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # P1 unlocks at start
    P1 <= 0 POINTS
    # P2 unlocks 1 hour after start
    P2 <= +1:00
    # P3 unlocks after 2 hours OR when P1 is solved
    P3 <= (+2:00 OR P1)
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    current_time = timezone.now()
    
    # Process at start
    team.process_unlocks()
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"

    # Process after 1 hour
    one_hour = timezone.timedelta(hours=1)
    with patch.object(timezone, 'now', return_value=current_time + one_hour):
        team.process_unlocks()
        unlocked = team.unlocked_puzzles()
        assert len(unlocked) == 2
        assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Process after 2 hours
    two_hours = timezone.timedelta(hours=2)
    with patch.object(timezone, 'now', return_value=current_time + two_hours):
        team.process_unlocks()
        unlocked = team.unlocked_puzzles()
        assert len(unlocked) == 3
        assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

def test_config_error_handling(hunt_with_puzzles):
    """Test error handling in config parsing and processing"""
    hunt, puzzles = hunt_with_puzzles

    # Test invalid puzzle reference
    config = """
    # Reference to non-existent puzzle
    P4 <= P1
    P1 <= 0 POINTS
    """
    with pytest.raises(ValidationError) as exc_info:
        hunt.config = config
        hunt.full_clean()
    assert "config" in exc_info.value.message_dict

    # Test invalid syntax
    config = """
    P1 <= <<invalid>>
    """
    with pytest.raises(ValidationError) as exc_info:
        hunt.config = config
        hunt.full_clean()
    assert "config" in exc_info.value.message_dict

    # Test circular dependency
    config = """
    P1 <= P2
    P2 <= P3
    P3 <= P1
    """
    with pytest.raises(ValidationError) as exc_info:
        hunt.config = config
        hunt.full_clean()
    assert "config" in exc_info.value.message_dict

def test_time_handling(hunt_with_puzzles):
    """Test time-based behavior including before hunt start and playtesters"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    P1 <= 0 POINTS
    P2 <= +1:00
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    # Test regular team before hunt starts
    future_start = timezone.now() + timezone.timedelta(days=1)
    hunt.start_date = future_start
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Nothing should unlock before hunt starts
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 0

    # Test playtest team with specific window
    playtest_team = Team.objects.create(
        name="Playtest Team",
        hunt=hunt,
        playtester=True,
        playtest_start_date=timezone.now(),
        playtest_end_date=timezone.now() + timezone.timedelta(days=2)
    )
    playtest_team.process_unlocks()

    # P1 should unlock for playtesters even though hunt hasn't started
    unlocked = playtest_team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"

def test_multiple_rewards(hunt_with_puzzles):
    """Test rules that give multiple rewards upon completion"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # P1 unlocks at start
    P1 <= 0 POINTS
    # Solving P1 unlocks P2 and gives points
    [P2, 5 POINTS] <= P1
    # Solving P2 unlocks P3 and gives points and hints
    [P3, 5 POINTS, 2 HINTS] <= P2
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Initially only P1 unlocked
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"
    assert team.points == 0
    team.refresh_from_db()
    assert team.num_available_hints == 0

    # Solve P1 to get P2 and points
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()
    team.refresh_from_db()

    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]
    assert team.points == 5
    assert team.num_available_hints == 0

    # Solve P2 to get P3, more points, and hints
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[1])
    status.mark_solved()
    team.process_unlocks()
    team.refresh_from_db()

    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]
    assert team.points == 10
    assert team.num_available_hints == 2

def test_complex_nested_rules(hunt_with_puzzles):
    """Test complex combinations of AND/OR with SomeOf rules"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzles unlock at start
    P1 <= 0 POINTS
    P2 <= 0 POINTS
    # P3 unlocks with complex rule:
    # Either (2 of [P1, P2] AND 15 points) OR (P1 AND 5 POINTS)
    P3 <= ((2 OF (P1, P2) AND 15 POINTS) OR (P1 AND 5 POINTS))
    # Give points for solving puzzles
    5 POINTS <= P1
    10 POINTS <= P2
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Initially P1 and P2 should be unlocked
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Solve P1 to get 5 points (satisfies P1 AND 5 POINTS condition)
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()

    # P3 should unlock (second condition met: P1 AND 5 POINTS)
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

    # Test with a second team taking the other path
    team2 = Team.objects.create(name="Test Team 2", hunt=hunt)
    team2.process_unlocks()

    # Initially P1 and P2 should be unlocked
    unlocked = team2.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Solve P2 first to get 10 points (not enough for either condition)
    status = PuzzleStatus.objects.get(team=team2, puzzle=puzzles[1])
    status.mark_solved()
    team2.process_unlocks()

    # P3 should not unlock yet (no conditions met)
    unlocked = team2.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Now solve P1 to get another 5 points and satisfy 2 OF (P1, P2) AND 15 POINTS
    status = PuzzleStatus.objects.get(team=team2, puzzle=puzzles[0])
    status.mark_solved()
    team2.process_unlocks()

    # P3 should unlock (first condition met: 2 OF (P1, P2) AND 15 POINTS)
    unlocked = team2.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

def test_nested_parentheses(hunt_with_puzzles):
    """Test that deeply nested parentheses in rules parse correctly"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzles unlock at start
    P1 <= 0 POINTS
    P2 <= 0 POINTS
    # Complex nested conditions
    P3 <= (((P1 AND (5 POINTS OR (P2 AND 10 POINTS))) OR (2 OF (P1, (P2 AND 15 POINTS), 20 POINTS))))
    # Give points for solving puzzles
    5 POINTS <= P1
    10 POINTS <= P2
    """
    hunt.config = config
    hunt.full_clean()  # Verify the config parses successfully
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Initially P1 and P2 should be unlocked
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Solve P1 to get 5 points
    # This satisfies (P1 AND 5 POINTS) in the first branch
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()

    # P3 should unlock (first branch satisfied: P1 AND (5 POINTS OR (P2 AND 10 POINTS)))
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

    # Test second team taking different path
    team2 = Team.objects.create(name="Test Team 2", hunt=hunt)
    team2.process_unlocks()

    # Solve P2 first to get 10 points
    status = PuzzleStatus.objects.get(team=team2, puzzle=puzzles[1])
    status.mark_solved()
    team2.process_unlocks()

    # P3 should not unlock yet (no complete conditions met)
    unlocked = team2.unlocked_puzzles()
    assert len(unlocked) == 2
    assert sorted([p.id for p in unlocked]) == ["1", "2"]

    # Solve P1 to get another 5 points (total 15 points)
    # This satisfies 2 OF (P1, (P2 AND 15 POINTS), 20 POINTS)
    status = PuzzleStatus.objects.get(team=team2, puzzle=puzzles[0])
    status.mark_solved()
    team2.process_unlocks()

    # P3 should unlock (second branch satisfied: 2 OF conditions met)
    unlocked = team2.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

def test_px_pattern_expansion(hunt_with_puzzles):
    """Test that PX patterns are correctly expanded for all puzzle IDs"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzles unlock with points
    PX <= 0 POINTS
    # Give points for solving puzzles
    5 POINTS <= PX
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    team.process_unlocks()
    
    # Initially all puzzles should be unlocked since PX <= 0 POINTS expands to all puzzles
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 3
    assert sorted([p.id for p in unlocked]) == ["1", "2", "3"]

    # Solve first puzzle to get points
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()

    # Should have 5 points from solving P1
    assert team.points == 5

    # Solve second puzzle to get more points
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[1])
    status.mark_solved()
    team.process_unlocks()

    # Should have 10 points total from solving P1 and P2
    assert team.points == 10

def test_puzzle_hint_rules(hunt_with_puzzles):
    """Test that puzzle-specific hint unlocking rules work correctly"""
    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzle unlocks with points
    P1 <= 0 POINTS
    P2 <= 0 POINTS
    # Get general hints for solving puzzles
    2 HINTS <= P1
    # Get puzzle-specific hints
    3 P1 HINTS <= P2
    2 P2 HINTS <= P1
    # Get puzzle hints every hour
    1 P1 HINT <= EVERY 1 HOUR
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    
    # Process unlocks at start
    team.process_unlocks()
    assert team.num_available_hints == 0
    
    # Check P1 and P2 are unlocked with no hints
    p1_status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    p2_status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[1])
    assert p1_status.num_available_hints == 0
    assert p1_status.num_total_hints_earned == 0
    assert p2_status.num_available_hints == 0
    assert p2_status.num_total_hints_earned == 0

    # Solve P1 to get general hints and P2-specific hints
    p1_status.mark_solved()
    team.process_unlocks()
    assert team.num_available_hints == 2
    p2_status.refresh_from_db()
    assert p2_status.num_available_hints == 2  # 2 hints for P2
    assert p2_status.num_total_hints_earned == 2

    # Solve P2 to get P1-specific hints
    p2_status.mark_solved()
    team.process_unlocks()
    assert team.num_available_hints == 2  # Unchanged
    p1_status.refresh_from_db()
    assert p1_status.num_available_hints == 3  # 3 hints for P1
    assert p1_status.num_total_hints_earned == 3
    assert p2_status.num_available_hints == 2  # Still 2 hints for P2
    assert p2_status.num_total_hints_earned == 2

    # Process after 1 hour to get additional P1 hint
    one_hour = timezone.timedelta(hours=1)
    current_time = timezone.now()
    with patch.object(timezone, 'now', return_value=current_time + one_hour) as mock_now:
        team.process_unlocks()
        assert team.num_available_hints == 2  # Unchanged
        p1_status.refresh_from_db()
        p2_status.refresh_from_db()
        assert p1_status.num_available_hints == 4  # One more hint for P1
        assert p1_status.num_total_hints_earned == 4
        assert p2_status.num_available_hints == 2  # Still 2 hints for P2
        assert p2_status.num_total_hints_earned == 2

def test_process_config_rules_looping(hunt_with_puzzles):
    """Test that process_config_rules properly loops when changes cascade."""

    hunt, puzzles = hunt_with_puzzles
    config = """
    # Initial puzzle unlocked
    P1 <= 0 POINTS
    # Chain reaction of points after solving P1
    3 POINTS <= P1
    3 POINTS <= 3 POINTS
    3 POINTS <= 6 POINTS
    P2 <= 9 POINTS
    """
    hunt.config = config
    hunt.full_clean()
    hunt.save()

    team = Team.objects.create(name="Test Team", hunt=hunt)
    
    # Initial state - just P1 unlocked
    team.process_unlocks()
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 1
    assert unlocked[0].id == "1"
    assert team.points == 0

    print("Solving P1")
    # Solve P1 - this should trigger the chain reaction in a single process_unlocks:
    # 1. Get 3 points from solving P1
    # 2. Having 3 points gives 3 more points (total 6)
    # 3. Having 6 points gives 3 more points (total 9)
    # 4. Having 9 points unlocks P2
    status = PuzzleStatus.objects.get(team=team, puzzle=puzzles[0])
    status.mark_solved()
    team.process_unlocks()
    
    # Verify everything happened in that single process_unlocks call
    unlocked = team.unlocked_puzzles()
    assert len(unlocked) == 2  # Both puzzles should be unlocked
    assert sorted([p.id for p in unlocked]) == ["1", "2"]
    assert team.points == 9  # Should have all points