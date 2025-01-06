from huey import crontab
from huey.contrib.djhuey import periodic_task, task
from django.utils import timezone
from .models import Team

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
    
    # Process unlocks for all active teams
    for team in regular_teams | playtest_teams:
        team.process_unlocks()