import io
from collections import Counter
import json
import shutil
from pathlib import Path
from zipfile import ZipFile
import csv

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import SuspiciousOperation
from django.core.files import File
from django.core.paginator import Paginator
from django.forms import ValidationError
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import F, Max, Count, Subquery, OuterRef, PositiveIntegerField, Min
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.template.loader import engines
from django.db.models import Q, F, Prefetch
from django.http import JsonResponse
from django.core import serializers

from django_sendfile import sendfile
from .utils import create_media_files, get_media_file_model, get_media_file_parent_model, create_hunt_export_zip, import_hunt_from_zip, import_hunt_from_zip, validate_hunt_zip
from .hunt_views import protected_static
from .models import Hunt, Team, Event, PuzzleStatus, Submission, Hint, User, Puzzle, SolutionFile, HuntFile
from .tasks import import_hunt_background
from .config_parser import parse_config, process_config_rules


@staff_member_required
def staff_base(request):
    """
    View function for the staff dashboard/index page.
    """
    hunt = get_object_or_404(Hunt, is_current_hunt=True)
    
    # Get team count for the current hunt
    team_count = Team.objects.filter(hunt=hunt).count()
    
    # Pass current time for template to use in time calculations
    now = timezone.now()
    
    context = {
        "hunt": hunt,
        "team_count": team_count,
        "now": now,
    }
    
    return render(request, "staff_index.html", context)


@staff_member_required
def feed(request, hunt):
    events = Event.objects.filter(hunt=hunt)

    puzzle_ids = []
    team_ids = []
    tags = request.GET.getlist("tags", [])
    for tag in tags:
        if tag.startswith("p:"):
            puzzle_ids.append(int(tag[2:]))
        elif tag.startswith("t:"):
            team_ids.append(int(tag[2:]))
    if len(puzzle_ids) > 0:
        events = events.filter(puzzle__in=puzzle_ids)
    if len(team_ids) > 0:
        events = events.filter(team__in=team_ids)

    checkboxes = request.GET.get("checkboxes", "all")
    if checkboxes != "all":
        types = checkboxes.split(",")
        events = events.filter(type__in=types)
    else:
        events = events.filter(type__in=Event.queue_types)
    display_checkboxes = Event.queue_types if checkboxes == "all" else checkboxes.split(",")

    events = events.select_related('team', 'puzzle', 'user').order_by('-timestamp')

    num_items = int(request.GET.get("numItems", 25))

    page = request.GET.get("page", None)
    pages = Paginator(events, num_items)
    paged_events = pages.get_page(page)
    context = {"hunt": hunt, "feed_items": paged_events, "types": Event.queue_types, 'num_items': num_items,
               "puzzle_tags": puzzle_ids, "team_tags": team_ids, 'display_checkboxes': display_checkboxes}

    return render(request, "staff_feed.html", context)


@staff_member_required
def progress(request, hunt):
    """
    View function to display the progress of teams in the current hunt.

    Args:
        request (HttpRequest): The HTTP request object.
    """
    info_columns = hunt.teamrankingrule_set.order_by("rule_order").all()
    puzzles = hunt.puzzle_set.all()
    teams = hunt.team_set.all()
    
    page_size = request.GET.get("page_size")
    try:
        page_size = int(page_size) if page_size else None
    except ValueError:
        page_size = None

    context = {
        'hunt': hunt,
        'teams': teams,
        'puzzles': puzzles,
        'info_columns': info_columns,
        'page_size': page_size
    }
    return render(request, "staff_progress.html", context)



@staff_member_required
def progress_data(request, hunt):
    """
    API endpoint to return progress data for DataTables consumption.
    """
    start_time = timezone.now()
    
    info_columns = hunt.teamrankingrule_set.order_by("rule_order").all()

    # Fetch puzzles with their stats
    puzzle_stats = [
        ('num_hints', '# Hints Used'),
        ('num_solves', '# Solves'),
        ('num_unlocks', '# Unlocks'),
        ('num_submissions', '# Submissions'),
    ]

    # Fetch puzzles
    puzzles = hunt.puzzle_set
    for stat in puzzle_stats:
        puzzles = Puzzle.annotate_query(puzzles, stat[0])
    puzzles = puzzles.all()

    # Fetch teams with their ranking data
    teams = hunt.active_teams
    for rule in info_columns:
        teams = rule.annotate_query(teams)
    teams = teams.order_by(*[rule.ordering_parameter for rule in info_columns]).all()

    # Fetch all puzzle statuses
    statuses = (PuzzleStatus.objects.filter(puzzle__hunt=hunt)
                .select_related('puzzle', 'team')
                .annotate(time_since=timezone.now() - F('unlock_time')))
    
    # Fetch submissions data
    submissions = (Submission.objects.filter(team__hunt=hunt)
                  .values('team', 'puzzle')
                  .annotate(last_submission=Max('submission_time'),
                           num_submissions=Count('*')))
    
    # Fetch hints data
    hints = (Hint.objects.filter(team__hunt=hunt)
            .values('team', 'puzzle')
            .annotate(num_hints=Count('*')))

    # Build response data
    response_data = {
        "data": [],
        "metadata": {
            "last_updated": timezone.now().isoformat(),
            "hunt_id": hunt.pk,
        }
    }

    # Create lookup dictionaries for faster access
    submission_data_lookup = {(s['team'], s['puzzle']): s for s in submissions}
    hint_data_lookup = {(h['team'], h['puzzle']): h for h in hints}
    status_lookup = {(s.team_id, s.puzzle_id): s for s in statuses}

    # Build team data
    for team in teams:
        team_data = {
            "team": {
                "id": team.pk,
                "name": team.name,
            },
            "ranking_columns": {
                column.display_name: getattr(team, column.rule_type) for column in info_columns
            }
        }

        # Build puzzle data for this team
        puzzle_data = {}
        for puzzle in puzzles:
            status = status_lookup.get((team.pk, puzzle.pk))
            submission = submission_data_lookup.get((team.pk, puzzle.pk), {})
            hint = hint_data_lookup.get((team.pk, puzzle.pk), {})

            if status:
                puzzle_data[str(puzzle.pk)] = {
                    "unlock_time": status.unlock_time.isoformat() if status and status.unlock_time else None,
                    "solve_time": status.solve_time.isoformat() if status and status.solve_time else None,
                    "last_submission": submission.get('last_submission').isoformat() if submission and submission.get('last_submission') else None,
                    "num_submissions": submission.get('num_submissions', 0) if submission else 0,
                    "num_hints": hint.get('num_hints', 0) if hint else 0
                }

        team_data["puzzles"] = puzzle_data
        response_data["data"].append(team_data)

    end_time = timezone.now()
    response_data["metadata"]["calculation_time_ms"] = (end_time - start_time).total_seconds() * 1000

    return JsonResponse(response_data)


@staff_member_required
def participant_info(request, hunt):
    """
    View function to display participant information for the current hunt.
    """
    # Get regular (non-playtester) teams and their participants
    regular_teams = hunt.team_set.filter(playtester=False)
    regular_participants = User.objects.filter(team__in=regular_teams).distinct()
    
    # Calculate statistics
    stats = {
        'total_participants': User.objects.filter(team__hunt=hunt).distinct().count(),
        'total_teams': hunt.team_set.count(),
        'regular_teams': regular_teams.count(),
        'regular_participants': regular_participants.count(),
        'playtest_teams': hunt.team_set.filter(playtester=True).count()
    }
    
    # Generate email string for clipboard
    emails_string = ', '.join([user.email for user in regular_participants])
    
    context = {
        'hunt': hunt,
        'stats': stats,
        'emails_string': emails_string
    }
    return render(request, "staff_participant_info.html", context)


@staff_member_required
def download_emails(request, hunt):
    """
    Generate and download a CSV file with participant emails from non-playtester teams.
    """
    # Get all non-playtester teams with their members
    teams = hunt.team_set.filter(playtester=False).prefetch_related('members')
    
    # Create HTTP response with CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="hunt_{hunt.id}_participants.csv"'
    
    # Create CSV writer and write header
    writer = csv.writer(response)
    writer.writerow(['Email', 'Display Name', 'First Name', 'Last Name', 'Team'])
    
    # Write all participants directly from the teams loop
    for team in teams:
        for user in team.members.all():
            writer.writerow([
                user.email,
                user.display_name,
                user.first_name,
                user.last_name,
                team.name
            ])
    
    return response


@require_GET
@staff_member_required
def hints_view(request, hunt):
    """
    View function to display hints for the current hunt.

    This view fetches hints based on optional filters provided via GET parameters.
    The hints are paginated and rendered in the 'staff_hints.html' template.
    """
    # Fetch hints related to the current hunt
    hints = Hint.objects.filter(puzzle__hunt=hunt, canned_hint__isnull=True)

    # Optional filters from GET parameters
    team_id = request.GET.get("team_id", None)
    hint_status = request.GET.get("hint_status", None)
    puzzle_id = request.GET.get("puzzle_id", None)

    # Filter hints by team ID if provided
    if team_id:
        hints = hints.filter(team__pk=int(team_id))

    # Filter hints by puzzle ID if provided
    if puzzle_id:
        hints = hints.filter(puzzle__pk=puzzle_id)

    # Filter hints by hint status if provided
    if hint_status:
        if hint_status == "answered":
            hints = hints.exclude(response="")
        elif hint_status == "unanswered":
            hints = hints.filter(response="")
        elif hint_status == "claimed":
            hints = hints.exclude(responder=None).filter(response="")
        elif hint_status == "unclaimed":
            hints = hints.filter(responder=None)

    # Paginate the hints
    page = request.GET.get("page", None)
    hints = hints.select_related('team', 'puzzle', 'responder').order_by('-pk')
    pages = Paginator(hints, 20)
    paged_hints = pages.get_page(page)

    # Render the template with the context
    context = {'hunt': hunt, 'hints': paged_hints}
    return render(request, "staff_hints.html", context)


@require_POST
@staff_member_required
def hints_claim(request, pk):
    """
    Claim a hint for the current user.

    This view function allows a staff member to claim a hint by its primary key (pk).

    Args:
        pk (int): The primary key of the hint to be claimed.
    """
    hint = get_object_or_404(Hint, pk=pk).claim(request.user)
    return render(request, "partials/_hint_row.html", {'hint': hint})


@require_POST
@staff_member_required
def hints_release(request, pk):
    """
    Release a claimed hint.

    This view function allows a staff member to release a previously claimed hint by its primary key (pk).

    Args:
        pk (int): The primary key of the hint to be released.
    """
    hint = get_object_or_404(Hint, pk=pk).release()
    return render(request, "partials/_hint_row.html", {'hint': hint})


@staff_member_required
def hints_respond(request, pk):
    """
    Respond to a hint request.

    This view function allows a staff member to respond to a hint request by its primary key (pk).
    The response is taken from the POST data. If the 'response' key is not present in the POST data,
    a SuspiciousOperation exception is raised. The responded hint is then rendered in the '_hint_row.html'
    partial template.

    Args:
        pk (int): The primary key of the hint to be responded to.
    """
    if "response" not in request.POST:
        raise SuspiciousOperation
    hint = get_object_or_404(Hint, pk=pk).respond(request.user, request.POST.get("response"))
    return render(request, "partials/_hint_row.html", {'hint': hint})


@require_POST
@staff_member_required
def hints_refund(request, pk):
    """
    Refund a hint.

    This view function allows a staff member to refund a hint by its primary key (pk).

    Args:
        pk (int): The primary key of the hint to be refunded.
    """
    hint = get_object_or_404(Hint, pk=pk).refund()
    return render(request, "partials/_hint_row.html", {'hint': hint})


@require_POST
@staff_member_required
def get_modal(request, pk):
    """
    Get the modal for a hint.

    This view function gets the modal a hint by its primary key (pk). For use by htmx requests.

    Args:
        pk (int): The primary key of the hint for the modal.
    """
    hint = get_object_or_404(Hint, pk=pk)
    if 'claim' in request.POST:
        hint = hint.claim(request.user)

    previous_submissions = Submission.objects.filter(team=hint.team, puzzle=hint.puzzle).order_by('-submission_time')
    previous_hints = Hint.objects.filter(team=hint.team, puzzle=hint.puzzle).exclude(pk=hint.pk).order_by('-pk')
    context = {'hint': hint, 'previous_submissions': previous_submissions, 'previous_hints': previous_hints}
    return render(request, "partials/_staff_hint_modal.html", context)


@staff_member_required
def charts(request, hunt):
    """
    View function to display charts for the current hunt.
    """

    num_teams = hunt.active_teams.count()

    # First, get a subquery of the minimum solve time for each puzzle
    earliest_solves = PuzzleStatus.objects.filter(
        puzzle__hunt=hunt,
        solve_time__isnull=False,
        team__playtester=False
    ).values('puzzle').annotate(
        min_solve_time=Min('solve_time')
    )

    # Then use that to get the actual PuzzleStatus objects
    earliest_solve_statuses = PuzzleStatus.objects.filter(
        puzzle__hunt=hunt,
        solve_time__isnull=False,
        team__playtester=False
    ).filter(
        solve_time__in=Subquery(
            earliest_solves.values('min_solve_time')
        )
    ).select_related('puzzle', 'team').order_by('puzzle__order_number')

    # Build a lookup dict for earliest solves by puzzle id
    earliest_solve_lookup = {status.puzzle_id: status for status in earliest_solve_statuses}

    # Puzzle Statistics
    puzzle_stats = [
        ('num_hints', '# Hints Used'),
        ('num_solves', '# Solves'),
        ('num_unlocks', '# Unlocks'),
        ('num_submissions', '# Submissions'),
        ('avg_solve_time', 'Avg. Solve Time'),
    ]

    stats_puzzles = hunt.puzzle_set
    for stat in puzzle_stats:
        stats_puzzles = Puzzle.annotate_query(stats_puzzles, stat[0])
    stats_puzzles = stats_puzzles.order_by('order_number').all()

    chart_solves_data = []
    chart_submissions_data = []
    chart_hints_data = []

    for puzzle in stats_puzzles:
        # Submission count table
        sq = (Submission.objects.filter(team__pk=OuterRef('pk'), puzzle=puzzle).values('team', 'puzzle')
              .annotate(c=Count('*')).values('c'))
        num_subs = (puzzle.team_set.filter(puzzlestatus__solve_time__isnull=False)
                    .annotate(num_s=Subquery(sq, output_field=PositiveIntegerField())).values_list('num_s', flat=True))
        sub_table_full = sorted(list(Counter(num_subs).items()), key=lambda x: x[0])
        cutoff = 5
        sub_table = sub_table_full[:cutoff]
        if len(sub_table_full) > cutoff:
            sub_table.append((f"{int(sub_table[-1][0]) + 1}+", sum([x[1] for x in sub_table_full[cutoff:]])))
        puzzle.sub_table = sub_table

        # Commonly guessed wrong answers (submissions that didn't match any custom response)
        commonly_guessed_answers = (
            Submission.objects
            .filter(puzzle=puzzle, matched_response__isnull=True)
            .exclude(submission_text__iexact=puzzle.answer)
            .values('submission_text')
            .annotate(count=Count('submission_text'))
            .order_by('-count')[:6]
        )
        puzzle.commonly_guessed_answers = commonly_guessed_answers

        # First solve info
        earliest_solve = earliest_solve_lookup.get(puzzle.id)
        puzzle.first_solve_team = earliest_solve.team if earliest_solve else None
        puzzle.first_solve_time = earliest_solve.solve_time if earliest_solve else None
    
        # Solves chart data
        chart_solves_data.append({
            "name": puzzle.name,
            "locked": num_teams - (puzzle.num_unlocks or 0),
            "unlocked": (puzzle.num_unlocks or 0) - (puzzle.num_solves or 0),
            "solved": puzzle.num_solves or 0
        })

        # Submissions breakdown (for table and chart)
        # Count submissions that matched a custom response (excluding correct answers)
        custom_response_count = (
            Submission.objects
            .filter(puzzle=puzzle, matched_response__isnull=False)
            .exclude(submission_text__iexact=puzzle.answer)
            .count()
        )
        total_incorrect = (puzzle.num_submissions or 0) - (puzzle.num_solves or 0)
        puzzle.num_custom_response = custom_response_count
        puzzle.num_incorrect = total_incorrect - custom_response_count

        chart_submissions_data.append({
            "name": puzzle.name,
            "incorrect": puzzle.num_incorrect,
            "custom_response": puzzle.num_custom_response,
            "correct": puzzle.num_solves or 0
        })

        # Hints chart data
        chart_hints_data.append({
            "name": puzzle.name,
            "hints": puzzle.num_hints or 0
        })

    # Submissions over time chart data
    submission_hours = []
    subs = Submission.objects.filter(puzzle__hunt=hunt,
                                     submission_time__gte=hunt.start_date,
                                     submission_time__lte=hunt.end_date)
    subs = subs.values_list('submission_time__year',
                            'submission_time__month',
                            'submission_time__day',
                            'submission_time__hour')
    subs = subs.annotate(Count("id")).order_by('submission_time__year',
                                               'submission_time__month',
                                               'submission_time__day',
                                               'submission_time__hour')
    for sub in subs:
        time_string = "%02d/%02d/%04d - %02d:00" % (sub[1], sub[2], sub[0], sub[3])
        submission_hours.append({"hour": time_string, "amount": sub[4]})

    # Solves over time chart data
    solve_hours = []
    solves = PuzzleStatus.objects.filter(puzzle__hunt=hunt,
                                       solve_time__isnull=False,
                                       solve_time__gte=hunt.start_date,
                                       solve_time__lte=hunt.end_date)
    solves = solves.values_list('solve_time__year',
                               'solve_time__month',
                               'solve_time__day',
                               'solve_time__hour')
    solves = solves.annotate(Count("id")).order_by('solve_time__year',
                                                  'solve_time__month',
                                                  'solve_time__day',
                                                  'solve_time__hour')
    for solve in solves:
        time_string = "%02d/%02d/%04d - %02d:00" % (solve[1], solve[2], solve[0], solve[3])
        solve_hours.append({"hour": time_string, "amount": solve[4]})

    context = {
        'chart_solves_data': chart_solves_data,
        'chart_submissions_data': chart_submissions_data,
        'chart_submissions_by_time_data': submission_hours,
        'chart_solves_by_time_data': solve_hours,
        'chart_hints_data': chart_hints_data,
        'hunt': hunt,
        'stats_puzzles': stats_puzzles,
        'num_teams': num_teams,
    }
    return render(request, "staff_charts.html", context)


@staff_member_required
def search(request, hunt):
    """
    View function for searching users and teams.
    
    This view allows staff members to search for users and teams by name/email.
    Results are returned via HTMX for dynamic updates.
    """
    query = request.GET.get('q', '').strip()
    
    context = {
        'hunt': hunt,
        'query': query,
    }
    
    if query:
        # Search for users by email, display name, or full name, but only those in the selected hunt
        users = User.objects.filter(
            Q(email__icontains=query) |
            Q(display_name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            team__hunt=hunt  # Only include users with a team in this hunt
        ).prefetch_related(
            Prefetch(
                'team_set',
                queryset=Team.objects.filter(hunt=hunt),
                to_attr='current_team_list'
            )
        ).distinct()[:10]
        
        # Search for teams by name
        teams = Team.objects.filter(
            hunt=hunt,
            name__icontains=query
        ).select_related('hunt').prefetch_related(
            'members',
            Prefetch(
                'puzzle_statuses',
                queryset=Puzzle.objects.filter(
                    puzzlestatus__team__hunt=hunt, 
                    puzzlestatus__solve_time__isnull=False
                ).distinct(),
                to_attr='solved_puzzles_list'
            )
        ).order_by('-hunt__display_start_date')[:10]
        
        context.update({
            'users': users,
            'teams': teams,
        })
    
    return render(request, "partials/_search_results.html", context)


def get_hunt_template_errors(template_text, hunt, request):
    team = Team(
        name="Preview Team",
        hunt=hunt,
    )
    puzzle_list = hunt.puzzle_set.all()

    puzzles = sorted(puzzle_list, key=lambda p: p.order_number)
    solved = []
    context = {'hunt': hunt, 'puzzles': puzzles, 'team': team, 'solved': solved}

    try:
        # Get the default Django template engine
        default_engine = engines['django']
        # Create a template instance
        template = default_engine.from_string(template_text)
        template.render(context, request=request)
    except Exception as e:
        return f"Error rendering template: {e}"
    return None


@staff_member_required
def hunt_template(request, hunt):
    # Take text from the template_text parameter and save it to the hunt's template file
    if request.method == "POST":
        template_text = request.POST.get("template_text", "")
        if template_text == "":
            messages.success(request, "Template cleared")
            hunt.template_file = None
            hunt.save()
        else:
            template_errors = get_hunt_template_errors(template_text, hunt, request)
            if template_errors is not None:
                messages.error(request, template_errors)
            else:
                with io.BytesIO() as buf:
                    buf.write(template_text.encode("utf-8"))
                    buf.seek(0)
                    template_file = File(buf, "template.html")
                    hunt.template_file = template_file
                    hunt.save()
                messages.success(request, "Template saved")
    else:
        template_text = ""
        if hunt.template_file is not None and hunt.template_file != "":
            template_text = hunt.template_file.file.read().decode("utf-8")
    context = {'hunt': hunt, 'template_text': template_text, 'puzzle_numbers': hunt.puzzle_set.values_list('order_number', flat=True)}
    return render(request, "staff_hunt_template.html", context)


@require_POST
@staff_member_required
def preview_template(request, hunt):
    template_text = request.POST.get("template_text", "")
    solved_arg = request.POST.get("solved", "")
    solved = [] if solved_arg == "" else [int(x) for x in solved_arg.split(",")]

    unlocked_arg = request.POST.get("unlocked", "")
    unlocked = [] if unlocked_arg == "" else [int(x) for x in unlocked_arg.split(",")]
    puzzle_list = hunt.puzzle_set.filter(order_number__in=unlocked)
    puzzles = sorted(puzzle_list, key=lambda p: p.order_number)

    solved = hunt.puzzle_set.filter(order_number__in=solved)
    context = {'hunt': hunt, 'puzzles': puzzles, 'team': Team(name="Preview Team", hunt=hunt), 'solved': solved}

    try:
        # Get the default Django template engine
        default_engine = engines['django']
        # Create a template instance
        template = default_engine.from_string(template_text)
        return HttpResponse(template.render(context, request=request))
    except Exception as e:
        return HttpResponse(f"Error rendering template: {e}")


@staff_member_required
def view_hunts(request, hunt):
    """
    View the list of hunts.

    This view function retrieves all hunts ordered by start date with the current hunt first.
    The hunts are then rendered in the 'staff_hunts.html' template.
    """
    hunts = Hunt.objects.order_by('-is_current_hunt', '-display_start_date')
    
    # For each hunt, get the end date of the previous hunt
    hunts = hunts.annotate(
        prev_hunt_end=Subquery(
            Hunt.objects.filter(
                display_end_date__lt=OuterRef('display_start_date')
            ).order_by('-display_end_date')
            .values('display_end_date')[:1]
        )
    )
    
    # Annotate total users and new users for each hunt
    hunts = hunts.annotate(
        total_users=Count('team__members', distinct=True),
        new_users=Count(
            'team__members',
            distinct=True,
            filter=Q(team__members__date_joined__gt=F('prev_hunt_end'))
        )
    ).all()
    
    return render(request, "staff_hunts.html", {'hunt': hunt, 'hunts': hunts})


@require_POST
@staff_member_required
def hunt_set_current(request, hunt):
    """
    Set a hunt as the current hunt.

    This view function sets the specified hunt as the current hunt and saves it.
    The updated list of hunts is then rendered in the 'staff_hunts.html' template.

    Args:
        hunt (Hunt): The hunt to be set as the current hunt.
    """
    hunt.is_current_hunt = True
    hunt.save()
    hunts = Hunt.objects.order_by('-is_current_hunt', '-display_start_date').all()
    return render(request, "staff_hunts.html", {'hunt': hunt, 'hunts': hunts})


@staff_member_required
def hunt_config(request, hunt):
    """Render or update the hunt configuration page."""
    if request.method == "POST":
        config_text = request.POST.get('config', '')
        try:
            hunt.config = config_text
            hunt.full_clean()  # This will validate the config
            hunt.save()
            messages.success(request, "Configuration saved successfully")
        except ValidationError as e:
            # Extract only the config validation error if it exists
            if 'config' in e.message_dict:
                messages.error(request, e.message_dict['config'][0])
            else:
                messages.error(request, str(e))
    else:
        config_text = hunt.config or "# Write your config here"
    
    return render(request, "staff_hunt_config.html", {'hunt': hunt, 'config_text': config_text})


@staff_member_required
def hunt_puzzles(request, hunt):
    """
    View function to display puzzles for the current hunt.

    This view fetches puzzles for a given hunt.
    The puzzles are then rendered in the 'staff_hunt_puzzles.html' template.

    Args:
        hunt (Hunt): The hunt instance for which to display puzzles
    """
    puzzles = list(hunt.puzzle_set.order_by('order_number').all())
    for i, puzzle in enumerate(puzzles):
        puzzle.has_gap = (puzzles[i].order_number - puzzles[i-1].order_number > 1) if i != 0 else False

    context = {'hunt': hunt, 'puzzles': puzzles}
    return render(request, "staff_hunt_puzzles.html", context)


@require_POST
@staff_member_required
def file_set_main(request, parent_type, pk):
    """
    Set a file as the main file for its parent object.

    This view function sets a specified file as the main file for its parent object.
    The type of main file is determined by the parent_type parameter.

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the file to be set as main.
    """
    model = get_media_file_model(parent_type)
    file = get_object_or_404(model, pk=pk)
    if model == SolutionFile:
        attr = "main_solution_file"
    elif model == HuntFile:
        attr = "css_file"
    else:
        attr = "main_file"
    if request.POST.get("mainFileSelected", "off") == "on":
        setattr(file.parent, attr, file)
    else:
        setattr(file.parent, attr, None)
    file.parent.save()

    context = {'parent': file.parent, 'parent_type': parent_type}
    return render(request, "partials/_staff_file_list.html", context)


@require_POST
@staff_member_required
def file_delete(request, parent_type, pk):
    """
    Delete a file.

    This view function deletes a specified file by its primary key (pk).

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the file to be deleted.
    """
    model = get_media_file_model(parent_type)
    file = get_object_or_404(model, pk=pk)
    file.delete()
    context = {'parent': file.parent, 'parent_type': parent_type}
    return render(request, "partials/_staff_file_list.html", context)


@require_POST
@staff_member_required
def file_replace(request, parent_type, pk):
    """
    Replace a file with a new upload.

    This view function replaces a specified file with a new uploaded file.

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the file to be replaced.
    """
    model = get_media_file_model(parent_type)
    file = get_object_or_404(model, pk=pk)
    uploaded_file = request.FILES.get('replaceFile', None)
    if uploaded_file is None:
        return HttpResponse("No file uploaded")
    with file.file.open('wb') as existing_file:
        for chunk in uploaded_file.chunks():
            existing_file.write(chunk)
    file.save()
    
    # Manually invalidate template cache if it's a template file
    if file.file.name.endswith('.tmpl'):
        from puzzlehunt.utils import invalidate_template_cache
        template_path = file.file.name.removeprefix("trusted/")
        invalidate_template_cache(template_path)

    context = {'parent': file.parent, 'swapped_pk': file.pk, 'parent_type': parent_type}
    return render(request, "partials/_staff_file_list.html", context)


@require_GET
@staff_member_required
def file_download(request, parent_type, pk):
    """
    Download a file.

    This view function allows a staff member to download a specified file by its primary key (pk).

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the file to be downloaded.
    """
    model = get_media_file_model(parent_type)
    file = get_object_or_404(model, pk=pk)
    return protected_static(request, file.parent.pk, file.relative_name, parent_type, True)


@require_POST
@staff_member_required
def file_delete_all(request, parent_type, pk):
    """
    Delete all files of a certain type for a parent object.

    This view function deletes all files of a specified parent_type type for a parent object.

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the parent object whose files are to be deleted.
    """
    model = get_media_file_parent_model(parent_type)
    parent = get_object_or_404(model, pk=pk)

    if parent_type == "solution":
        parent.solution_files.all().delete()
    else:
        parent.files.all().delete()
    context = {'parent': parent, 'parent_type': parent_type}
    return render(request, "partials/_staff_file_list.html", context)


@require_POST
@staff_member_required
def file_upload(request, parent_type, pk):
    """
    Upload one or more new files.

    This view function uploads one or more files and associates them with a parent object.
    It can handle both single file uploads and multiple file uploads.

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the parent object to which the files will be associated.
    """
    model = get_media_file_parent_model(parent_type)
    parent = get_object_or_404(model, pk=pk)

    all_created_files = []
    for uploaded_file in request.FILES.getlist('uploadFile'):
        created_files = create_media_files(parent, uploaded_file, parent_type == "solution")
        if isinstance(created_files, list):
            all_created_files.extend(created_files)

    context = {'parent': parent, 'parent_type': parent_type, 'uploaded_pks': [f.pk for f in all_created_files]}
    return render(request, "partials/_staff_file_list.html", context)


@staff_member_required
def export_hunt(request, hunt):
    temp_dir = Path(settings.MEDIA_ROOT) / 'exports' / f'hunt_{hunt.pk}_{timezone.now().timestamp()}'
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    include_activity = request.GET.get('include_activity', 'false').lower() == 'true'

    try:
        zip_path = temp_dir.with_suffix('.phe')
        create_hunt_export_zip(hunt, zip_path, include_activity)

        response = sendfile(request, str(zip_path), attachment=True, attachment_filename=f"{hunt.name}.phe")
        response['Content-Disposition'] = f'attachment; filename="{hunt.name}.phe"'
        return response
        
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@require_POST
@staff_member_required
def import_hunt(request, hunt):
    """
    Import a hunt from a zip file.
    
    This view accepts a zip file upload and queues it for background processing.
    The zip file should have been created by the export_hunt view.
    """
    if 'hunt_file' not in request.FILES:
        messages.error(request, "No file was uploaded")
        return render(request, "staff_hunts.html", {'hunt': hunt, 'hunts': Hunt.objects.order_by('-is_current_hunt', '-display_start_date').all()})
    
    hunt_file = request.FILES['hunt_file']
    include_activity = request.POST.get('include_activity', 'false').lower() == 'true'
    
    # Create a temporary directory to store the uploaded file
    temp_dir = Path(settings.MEDIA_ROOT) / 'imports' / f'hunt_import_{timezone.now().timestamp()}'
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save the uploaded file
        zip_path = temp_dir.with_suffix('.phe')
        with open(zip_path, 'wb+') as destination:
            for chunk in hunt_file.chunks():
                destination.write(chunk)

        # Validate the zip file before queueing
        validate_hunt_zip(zip_path, include_activity)

        # Queue the import task
        import_hunt_background(str(zip_path), include_activity)
        messages.success(request, "Hunt import queued successfully. This may take a few minutes.")
    except ValidationError as e:
        # Clean up the temporary file
        if zip_path.exists():
            zip_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        messages.error(request, f"Invalid hunt file: {str(e)}")
    except Exception as e:
        # Clean up the temporary file
        if zip_path.exists():
            zip_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        messages.error(request, f"Error importing hunt: {str(e)}")

    return view_hunts(request, hunt)

@require_POST
@staff_member_required
def hunt_reset(request, hunt):
    hunt.reset()
    return view_hunts(request, hunt)


@dataclass
class MockPuzzleStatus:
    """Mock PuzzleStatus for config testing without database records."""
    puzzle_id: str
    unlock_time: object  # datetime or None
    solve_time: object  # datetime or None


@staff_member_required
def config_tester(request, hunt):
    """
    View for testing hunt configuration without creating actual team data.
    Simulates puzzle unlocks based on provided solved states and time.
    """
    puzzles = hunt.puzzle_set.order_by('order_number').all()
    puzzle_ids = set(str(p.id) for p in puzzles)
    order_to_id = {p.order_number: str(p.id) for p in puzzles}

    # Parse simulated time offset from URL params as integer minutes (default: 0)
    time_offset_mins = int(request.GET.get('t', 0))
    simulated_time = hunt.start_date + timedelta(minutes=time_offset_mins)

    # Build mock puzzle statuses from URL params
    # Format: s_<puzzle_id>=<minutes> (minutes from hunt start when solved)
    mock_statuses = []
    solved_puzzle_ids = set()
    solve_times_mins = {}  # puzzle_id -> integer minutes

    for puzzle in puzzles:
        solve_mins_param = request.GET.get(f's_{puzzle.id}')
        if solve_mins_param is not None:
            try:
                solve_mins = int(solve_mins_param)
                solve_time = hunt.start_date + timedelta(minutes=solve_mins)
                # Assume unlock time is slightly before solve time (or at hunt start)
                unlock_time = max(hunt.start_date, solve_time - timedelta(minutes=1))
                mock_statuses.append(MockPuzzleStatus(
                    puzzle_id=str(puzzle.id),
                    unlock_time=unlock_time,
                    solve_time=solve_time
                ))
                solved_puzzle_ids.add(str(puzzle.id))
                solve_times_mins[str(puzzle.id)] = solve_mins
            except ValueError:
                pass  # Ignore invalid values

    # Parse and process config rules
    unlocked_puzzles = set()
    points = 0
    hints = 0
    puzzle_hints = {}
    earned_badges = []
    parse_error = None

    if hunt.config and hunt.config.strip():
        try:
            config_rules = parse_config(hunt.config, puzzle_ids, order_to_id)
            unlocked_puzzles, points, hints, puzzle_hints, earned_badges = process_config_rules(
                config_rules,
                mock_statuses,
                hunt.start_date,
                simulated_time
            )
        except Exception as e:
            parse_error = str(e)

    # Build puzzle data for template
    puzzle_data = []
    for puzzle in puzzles:
        pid = str(puzzle.id)
        puzzle_data.append({
            'puzzle': puzzle,
            'is_solved': pid in solved_puzzle_ids,
            'is_unlocked': pid in unlocked_puzzles,
            'solve_time_mins': solve_times_mins.get(pid),
            'puzzle_hints': puzzle_hints.get(pid, 0),
        })

    context = {
        'hunt': hunt,
        'puzzle_data': puzzle_data,
        'time_offset_mins': time_offset_mins,
        'simulated_time': simulated_time,
        'points': points,
        'hints': hints,
        'earned_badges': earned_badges,
        'parse_error': parse_error,
        'num_unlocked': len(unlocked_puzzles),
        'num_solved': len(solved_puzzle_ids),
    }

    return render(request, "staff_config_tester.html", context)


@staff_member_required
def file_editor(request, hunt):
    """
    Main file editor page with three-panel selector and Ace editor.
    """
    hunts = Hunt.objects.order_by('-start_date').all()

    # Check for pre-selected file from query params
    preselect_type = request.GET.get('type')
    preselect_file_pk = request.GET.get('file')

    context = {
        'hunt': hunt,
        'hunts': hunts,
        'preselect_type': preselect_type,
        'preselect_file_pk': preselect_file_pk,
    }
    return render(request, "staff_file_editor.html", context)


@require_GET
@staff_member_required
def file_editor_puzzle_list(request):
    """
    HTMX endpoint returning puzzle select dropdown for a given hunt.
    """
    hunt_id = request.GET.get('hunt_id')
    if not hunt_id:
        return render(request, "partials/_file_editor_puzzle_select.html", {
            'hunt': None,
            'puzzles': [],
            'hunt_has_files': False,
        })

    hunt = get_object_or_404(Hunt, pk=hunt_id)
    puzzles = hunt.puzzle_set.order_by('order_number').all()

    # Filter to only puzzles that have editable files
    puzzles_with_files = []
    for puzzle in puzzles:
        if puzzle.files.exists() and any(f.is_text_editable for f in puzzle.files.all()):
            puzzles_with_files.append(puzzle)

    context = {
        'hunt': hunt,
        'puzzles': puzzles_with_files,
        'hunt_has_files': hunt.files.exists() and any(f.is_text_editable for f in hunt.files.all()),
    }
    return render(request, "partials/_file_editor_puzzle_select.html", context)


@require_GET
@staff_member_required
def file_editor_file_list(request):
    """
    HTMX endpoint returning file select dropdown for a given puzzle or hunt.
    """
    # Parse parent value (format: "type:id")
    parent_value = request.GET.get('parent')
    if not parent_value or ':' not in parent_value:
        return render(request, "partials/_file_editor_file_select.html", {
            'files': [],
            'parent_type': None,
        })

    parent_type, parent_id = parent_value.split(':', 1)
    model = get_media_file_parent_model(parent_type)
    parent = get_object_or_404(model, pk=parent_id)

    if parent_type == "solution":
        files = parent.solution_files.all()
    else:
        files = parent.files.all()

    # Filter to only text-editable files
    editable_files = [f for f in files if f.is_text_editable]

    # Auto-select if only one file
    auto_select_file = editable_files[0] if len(editable_files) == 1 else None

    context = {
        'files': editable_files,
        'parent_type': parent_type,
        'auto_select_file': auto_select_file,
    }
    return render(request, "partials/_file_editor_file_select.html", context)


@require_GET
@staff_member_required
def file_editor_load_content(request):
    """
    HTMX endpoint returning the editor partial with file content.
    """
    file_value = request.GET.get('file')
    if not file_value or ':' not in file_value:
        return render(request, "partials/_file_editor_content.html", {'file': None})

    parent_type, file_pk = file_value.split(':', 1)
    model = get_media_file_model(parent_type)
    file = get_object_or_404(model, pk=file_pk)

    if not file.is_text_editable:
        return render(request, "partials/_file_editor_content.html", {'file': None})

    try:
        file.file.open('r')
        content = file.file.read()
        file.file.close()

        if isinstance(content, bytes):
            content = content.decode('utf-8')

        context = {
            'file': file,
            'content': content,
            'parent_type': parent_type,
        }
        return render(request, "partials/_file_editor_content.html", context)
    except Exception:
        return render(request, "partials/_file_editor_content.html", {'file': None})


@require_POST
@staff_member_required
def file_save_content(request, parent_type, pk):
    """
    Save edited content back to file.
    """
    from django.core.files.base import ContentFile
    from puzzlehunt.utils import invalidate_template_cache

    model = get_media_file_model(parent_type)
    file = get_object_or_404(model, pk=pk)

    if not file.is_text_editable:
        return JsonResponse({'error': 'Not a text-editable file'}, status=400)

    content = request.POST.get('content', '')

    with file.file.open('wb') as f:
        f.write(content.encode('utf-8'))
    file.save()

    # Manually invalidate template cache for template files
    if file.file.name.endswith('.tmpl') or file.file.name.endswith('.html'):
        template_path = file.file.name.removeprefix("trusted/")
        invalidate_template_cache(template_path)

    return JsonResponse({
        'success': True,
        'saved_at': timezone.now().isoformat(),
    })
