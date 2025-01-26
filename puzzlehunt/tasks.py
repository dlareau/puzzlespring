from huey import crontab
from huey.contrib.djhuey import periodic_task, task
from django.utils import timezone
from .models import Team
from .config_parser import parse_config
import logging
from pathlib import Path
from .utils import import_hunt_from_zip

logger = logging.getLogger(__name__)

@periodic_task(crontab(minute='*'))  # Runs every minute
def check_team_unlocks():
    """Check and process unlocks for all active teams in active hunts."""
    current_time = timezone.now()
    
    # Get regular teams in active hunts
    regular_teams = Team.objects.filter(
        playtester=False,
        hunt__start_date__lte=current_time,
        hunt__end_date__gte=current_time
    )
    
    # Get playtest teams in their playtest window
    playtest_teams = Team.objects.filter(
        playtester=True,
        playtest_start_date__lte=current_time,
        playtest_end_date__gte=current_time
    )

    hunt_configs = {}

    # Process unlocks for all active teams
    for team in regular_teams | playtest_teams:
        if team.hunt.id not in hunt_configs:
            puzzle_ids = set(team.hunt.puzzle_set.values_list('id', flat=True))
            try:
                # Parse the config and process unlocks
                config_rules = parse_config(team.hunt.config, puzzle_ids)
            except Exception as e:
                # Log the error if config parsing fails
                logger.error(f"Error processing hunt config: {e}")
                return
            hunt_configs[team.hunt.id] = config_rules

        team.process_unlocks(parsed_config=hunt_configs[team.hunt.id])

@task()
def import_hunt_background(zip_path: str, include_activity: bool = False) -> None:
    """
    Background task to import a hunt from a zip file.
    
    Args:
        zip_path: Path to the temporary zip file
        include_activity: Whether to include activity data
    """
    try:
        new_hunt = import_hunt_from_zip(zip_path, include_activity)
        # Clean up the temporary file
        if Path(zip_path).exists():
            Path(zip_path).unlink()
        return new_hunt.id
    except Exception as e:
        # Clean up on error
        if Path(zip_path).exists():
            Path(zip_path).unlink()
        raise e