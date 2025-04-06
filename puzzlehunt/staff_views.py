import io
from collections import Counter
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

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


@staff_member_required
def staff_base(request):
    return redirect('puzzlehunt:staff:hunts', hunt="current")


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
    puzzles = hunt.puzzle_set.order_by('order_number')
    teams = hunt.active_teams
    num_teams = teams.count()
    num_puzzles = puzzles.count()

    names = puzzles.values_list('name', flat=True)

    # Charts 1, 2 and 7
    puzzle_info_dict1 = []
    puzzle_info_dict2 = []
    puzzle_info_dict7 = []

    solves = puzzles.annotate(solved=Count('puzzlestatus', filter=Q(puzzlestatus__solve_time__isnull=False))).values_list('solved', flat=True)
    unlocks = puzzles.annotate(unlocked=Count('puzzlestatus', filter=Q(puzzlestatus__unlock_time__isnull=False))).values_list('unlocked', flat=True)
    subs = puzzles.annotate(subs=Count('submission')).values_list('subs', flat=True)
    hints = puzzles.annotate(hints=Count('hint')).values_list('hints', flat=True)
    puzzle_data = zip(names, solves, subs, unlocks, hints)
    for puzzle in puzzle_data:
        puzzle_info_dict1.append({
            "name": puzzle[0],
            "locked": num_teams - puzzle[3],
            "unlocked": puzzle[3] - puzzle[1],
            "solved": puzzle[1]
        })

        puzzle_info_dict2.append({
            "name": puzzle[0],
            "incorrect": puzzle[2] - puzzle[1],
            "correct": puzzle[1]
        })

        puzzle_info_dict7.append({
            "name": puzzle[0],
            "hints": puzzle[4]
        })

    # Chart 3
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

    # Chart 4
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

    # Info Table - Get earliest solve for each puzzle
    # First, get a subquery of the minimum solve time for each puzzle
    earliest_solves = PuzzleStatus.objects.filter(
        puzzle__hunt=hunt,
        solve_time__isnull=False,
        team__playtester=False
    ).values('puzzle').annotate(
        min_solve_time=Min('solve_time')
    )

    # Then use that to get the actual PuzzleStatus objects
    results = PuzzleStatus.objects.filter(
        puzzle__hunt=hunt,
        solve_time__isnull=False,
        team__playtester=False
    ).filter(
        solve_time__in=Subquery(
            earliest_solves.values('min_solve_time')
        )
    ).select_related('puzzle', 'team').order_by('puzzle__order_number')

    context = {'chart_solves_data': puzzle_info_dict1, 'chart_submissions_data': puzzle_info_dict2,
               'chart_submissions_by_time_data': submission_hours, 'chart_solves_by_time_data': solve_hours,
               'teams': teams, 'num_puzzles': num_puzzles, 'chart_rows': results, 'puzzles': puzzles,
               'chart_hints_data': puzzle_info_dict7, 'hunt': hunt}
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
        # Search for users by email, display name, or full name
        users = User.objects.filter(
            Q(email__icontains=query) |
            Q(display_name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).prefetch_related(
            Prefetch(
                'team_set',
                queryset=Team.objects.filter(hunt=hunt),
                to_attr='current_team_list'
            )
        ).distinct()[:10]
        
        # Search for teams by name
        teams = Team.objects.filter(
            name__icontains=query
        ).select_related('hunt').prefetch_related(
            'members',
            Prefetch(
                'puzzle_statuses',
                queryset=Puzzle.objects.filter(puzzlestatus__solve_time__isnull=False),
                to_attr='solved_puzzles_list'
            )
        ).order_by('-hunt__display_start_date')[:10]
        
        context.update({
            'users': users,
            'teams': teams,
        })
    
    if request.htmx:
        return render(request, "partials/_search_results.html", context)
        
    return render(request, "staff_search.html", context)


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
    solved = [int(x) for x in request.POST.get("solved", "").split(",")]

    unlocked = [int(x) for x in request.POST.get("unlocked", "").split(",")]
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

    This view fetches and annotates puzzles for a given hunt.
    The puzzles are then rendered in the 'staff_hunt_puzzles.html' template.

    Args:
        hunt (Hunt): The hunt instance for which to display puzzles
    """
    puzzle_stats = [
        ('num_hints', '# Hints Used'),
        ('num_solves', '# Solves'),
        ('num_unlocks', '# Unlocks'),
        ('num_submissions', '# Submissions'),
        ('avg_solve_time', 'Avg. Solve Time'),
    ]

    # Fetch puzzles
    puzzles = hunt.puzzle_set
    for stat in puzzle_stats:
        puzzles = Puzzle.annotate_query(puzzles, stat[0])
    puzzles = puzzles.all()

    for puzzle in puzzles:
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

        commonly_guessed_answers = Submission.objects.filter(puzzle=puzzle).values('submission_text').annotate(
            count=Count('submission_text')).order_by('-count')[:7]
        commonly_guessed_answers = [x for x in commonly_guessed_answers if
                                    x['submission_text'].lower() != puzzle.answer.lower()][:6]
        puzzle.commonly_guessed_answers = commonly_guessed_answers

    puzzles = list(puzzles)
    for i, puzzle in enumerate(puzzles):
        if i != 0:
            puzzle.has_gap = puzzles[i].order_number - puzzles[i-1].order_number > 1
        else:
            puzzle.has_gap = False

    context = {'hunt': hunt, 'puzzles': puzzles, 'num_teams': hunt.team_set.count()}
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
    Upload a new file.

    This view function uploads a new file and associates it with a parent object.

    Args:
        parent_type (str): The type of the parent (e.g., 'solution', 'hunt').
        pk (int): The primary key of the parent object to which the file will be associated.
    """
    model = get_media_file_parent_model(parent_type)
    parent = get_object_or_404(model, pk=pk)

    created_files = create_media_files(parent, request.FILES.get('uploadFile', None), parent_type == "solution")
    context = {'parent': parent, 'parent_type': parent_type, 'uploaded_pks': [f.pk for f in created_files]}
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
