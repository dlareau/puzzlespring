import io
from collections import Counter

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import SuspiciousOperation
from django.core.files import File
from django.core.paginator import Paginator
from django.template import Template, RequestContext, Engine
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from .utils import create_media_files, get_media_file_model, get_media_file_parent_model
from .hunt_views import protected_static
from .models import Hunt, Team, Event, PuzzleStatus, Submission, Hint, User, Puzzle, \
    PuzzleFile, SolutionFile, HuntFile
from django.shortcuts import render, get_object_or_404
from django.forms import inlineformset_factory
from django.db.models import F, Max, Count, Subquery, OuterRef, PositiveIntegerField
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.template.loader import engines
from puzzlehunt.config_parser import parse_config
from django.db.models import Q, F, Prefetch


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

    This view fetches and annotates puzzles and teams with various statistics, such as the number of hints used,
    solves, unlocks, and submissions. It also creates a table cell each team/puzzle combo, and adds submissions
    and hints to these cells. The progress data is then rendered in the 'staff_progress.html' template.

    Args:
        request (HttpRequest): The HTTP request object.
    """
    info_columns = hunt.teamrankingrule_set.order_by("rule_order").all()

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

    # Fetch teams
    teams = hunt.team_set
    for rule in info_columns:
        teams = rule.annotate_query(teams)
    teams = teams.order_by(*[rule.ordering_parameter for rule in info_columns]).all()

    # Create status arrays
    puzzle_pks = [puzzle.pk for puzzle in puzzles]
    team_pks = [team.pk for team in teams]
    team_idx_cache = {t.pk: team_pks.index(t.pk) for t in teams}
    puzzle_idx_cache = {p.pk: puzzle_pks.index(p.pk) for p in puzzles}
    for team in teams:
        team.statuses = [None for _ in puzzles]

    # Fill in status arrays
    statuses = PuzzleStatus.objects.filter(puzzle__hunt=hunt).select_related('puzzle').select_related('team')
    statuses = statuses.annotate(time_since=timezone.now() - F('unlock_time')).all()
    for status in statuses:
        puzzle_idx = puzzle_idx_cache[status.puzzle.pk]
        team_idx = team_idx_cache[status.team.pk]
        teams[team_idx].statuses[puzzle_idx] = status

    # Add submissions to status arrays
    submissions = Submission.objects.filter(team__hunt=hunt).values('team', 'puzzle')
    submissions = submissions.annotate(last_submission=Max('submission_time')).annotate(num_submissions=Count('*'))
    for sub in submissions:
        puzzle_idx = puzzle_idx_cache[sub['puzzle']]
        team_idx = team_idx_cache[sub['team']]
        if teams[team_idx].statuses[puzzle_idx] is not None:
            teams[team_idx].statuses[puzzle_idx].num_submissions = sub['num_submissions']
            teams[team_idx].statuses[puzzle_idx].last_submission = sub['last_submission']

    # Add hints to status arrays
    hints = Hint.objects.filter(team__hunt=hunt).values('team', 'puzzle').annotate(num_hints=Count('*'))

    for hint in hints:
        puzzle_idx = puzzle_idx_cache[hint['puzzle']]
        team_idx = team_idx_cache[hint['team']]
        if teams[team_idx].statuses[puzzle_idx] is not None:
            teams[team_idx].statuses[puzzle_idx].num_hints = hint['num_hints']

    context = {'hunt': hunt, 'teams': teams, 'puzzles': puzzles, 'info_columns': info_columns, 'puzzle_stats': puzzle_stats}
    return render(request, "staff_progress.html", context )


@require_GET
@staff_member_required
def hints_view(request, hunt):
    """
    View function to display hints for the current hunt.

    This view fetches hints based on optional filters provided via GET parameters.
    The hints are paginated and rendered in the 'staff_hints.html' template.
    """
    # Fetch hints related to the current hunt
    hints = Hint.objects.filter(puzzle__hunt=hunt)

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
    return render(request, "staff_charts.html", {'hunt': hunt})


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
        # Get the config from the request body
        config_text = request.POST.get('config', '')
        try:
            
            # Validate the config by attempting to parse it
            parse_config(config_text)
            # If parsing succeeds, save the config
            hunt.config = config_text
            hunt.save()
            messages.success(request, "Configuration saved successfully")
        except Exception as e:
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

    create_media_files(parent, request.FILES.get('uploadFile', None), parent_type == "solution")
    context = {'parent': parent, 'parent_type': parent_type}
    return render(request, "partials/_staff_file_list.html", context)