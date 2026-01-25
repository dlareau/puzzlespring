import time

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
    task_start = time.perf_counter()
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

    all_teams = list(regular_teams | playtest_teams)
    query_time = time.perf_counter() - task_start

    hunt_configs = {}
    config_time = 0.0
    process_time = 0.0

    # Process unlocks for all active teams
    for team in all_teams:
        if team.hunt.id not in hunt_configs:
            config_start = time.perf_counter()
            puzzles = team.hunt.puzzle_set.values_list('id', 'order_number')
            puzzle_ids = set(p[0] for p in puzzles)
            order_to_id = {p[1]: p[0] for p in puzzles}
            try:
                # Parse the config and process unlocks
                config_rules = parse_config(team.hunt.config, puzzle_ids, order_to_id)
            except Exception as e:
                # Log the error if config parsing fails
                logger.error(f"Error processing hunt config: {e}")
                return
            hunt_configs[team.hunt.id] = config_rules
            config_time += time.perf_counter() - config_start

        process_start = time.perf_counter()
        team.process_unlocks(parsed_config=hunt_configs[team.hunt.id])
        process_time += time.perf_counter() - process_start

    total_time = time.perf_counter() - task_start
    logger.info(
        f"check_team_unlocks: total={total_time:.3f}s, query={query_time:.3f}s, "
        f"config={config_time:.3f}s, process={process_time:.3f}s, "
        f"teams={len(all_teams)}, hunts={len(hunt_configs)}"
    )

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