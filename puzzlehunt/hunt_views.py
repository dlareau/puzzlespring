from crispy_forms.utils import render_crispy_form
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db.models import F, Max, Count
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.urls import reverse_lazy
from pathlib import Path
from django.template.loader import render_to_string


from django.views.decorators.http import require_POST
from django_eventstream import send_event
from django_htmx.http import retarget, reswap
from django_ratelimit.core import get_usage
from django_sendfile import sendfile

from .forms import AnswerForm
from .models import (Puzzle, Hunt, Submission, Prepuzzle, Hint, PuzzleStatus, Update,
                     PuzzleFile, SolutionFile, HuntFile, PrepuzzleFile, Team)
from .utils import get_media_file_model

import logging
logger = logging.getLogger(__name__)

DT_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def protected_static(request, pk, file_path, base="puzzle", add_prefix=False):
    """
    A view to serve protected static content. If the permission check passes, the file is served via X-Sendfile.
    """
    object_type = get_media_file_model(base)

    if add_prefix:
        file_path = f"trusted/{base}/{pk}/files/{file_path}"
    else:
        file_path = f"trusted/{base}/{pk}/{file_path}"

    media_file = get_object_or_404(object_type, file=file_path)
    if media_file.check_access(request.user):
        # TODO: Add back in the concept of a "safe name" for all static parent objects and call it here.
        sendfile_response = sendfile(request, file_path, attachment_filename=f"{base}_{pk}_{Path(file_path).name}")
        if base == "solution":
            sendfile_response['X-Robots-Tag'] = 'noindex'
        return sendfile_response
    else:
        logger.info("User %s tried to access %s and failed." % (str(request.user), file_path))

    return HttpResponseNotFound('<h1>Page not found</h1>')


def puzzle_view(request, pk):
    puzzle = get_object_or_404(Puzzle, pk=pk)
    team = puzzle.hunt.team_from_user(request.user)

    # Determine access
    # TODO: this is duplicative with the Puzzle.has_access method, but it would take more queries to get the 'solved'
    #       boolean, so ideally that could somehow be returned by that method.
    try:
        puzzle_status = PuzzleStatus.objects.get(puzzle=puzzle, team=team)
    except PuzzleStatus.DoesNotExist:
        puzzle_status = None
    has_access = False
    solved = False
    if puzzle.hunt.is_public or request.user.is_staff:
        has_access = True
    if team is not None and puzzle_status is not None and puzzle_status.unlock_time is not None:
        has_access = True
        solved = puzzle_status.solve_time is not None

    if not has_access:
        if request.user.is_authenticated:
            return render(request, 'access_error.html', {'reason': "puzzle"})
        else:
            return redirect('%s?next=%s' % (reverse_lazy(settings.LOGIN_URL), request.path))

    submissions = None
    if team is not None:
        submissions = Submission.objects.filter(team=team, puzzle=puzzle).order_by('-pk')

    updates = Update.objects.filter(puzzle=puzzle).all()
    context = {"puzzle": puzzle, "team": team, "solved": solved, "submissions": submissions, 'updates': updates,
               "form": AnswerForm(puzzle=puzzle, disable_form=solved)}
    if puzzle.main_file is None or not puzzle.main_file.extension == "tmpl":
        return render(request, "puzzle_non_template.html", context)
    else:
        return render(request, puzzle.main_file.file.name.removeprefix("trusted/"), context)


# TODO: give solutions the same template / no template treatment as puzzles
def puzzle_solution(request, pk):
    puzzle = get_object_or_404(Puzzle, pk=pk)
    if not puzzle.check_access(user=request.user, solution=True):
        return render(request, 'access_error.html', {'reason': "puzzle"})
    context = {"puzzle": puzzle}
    if puzzle.main_solution_file is None or not puzzle.main_solution_file.extension == "tmpl":
        return render(request, "puzzle_solution.html", context)
    else:
        return render(request, puzzle.main_solution_file.file.name.removeprefix("trusted/"), context)


def get_ratelimit_key(group, request):
    return request.ratelimit_key


@require_POST
def puzzle_submit(request, pk):
    puzzle = get_object_or_404(Puzzle, pk=pk)
    team = puzzle.hunt.team_from_user(request.user)

    # You must have access to the hunt and the puzzle to make a submission
    if not (puzzle.hunt.check_access(request.user) and puzzle.check_access(request.user)):
        raise SuspiciousOperation

    # Ratelimiting logic
    if not puzzle.hunt.is_public and not request.user.is_staff:
        if team is None:
            raise SuspiciousOperation

        usage = get_usage(request, fn=puzzle_submit, key=lambda _, r: str(pk) + str(team.pk),
                          rate='3/5m', method='POST', increment=True)
        if usage['should_limit']:
            form = AnswerForm(puzzle=puzzle)
            err_message = f"You have been rate limited. You can submit answers again in {usage['time_left']} seconds."
            form.errors['answer'] = [err_message]
            return HttpResponse(render_crispy_form(form))

    # Get submission and respond to it here
    form = AnswerForm(request.POST, puzzle=puzzle)
    if not form.is_valid():
        return HttpResponse(render_crispy_form(form))

    user_answer = form.cleaned_data['answer']
    s = Submission(submission_text=user_answer, team=team, puzzle=puzzle,
                   submission_time=timezone.now(), user=request.user)
    s.respond()
    if puzzle.hunt.is_public:
        response = render(request, "partials/_puzzle_public_response.html", context={'submission': s})
        return retarget(reswap(response, "outerHTML"), "#public-answer-status")

    if team is None and request.user.is_staff:
        form = AnswerForm(puzzle=puzzle)
        err_message = (f"You're a staff member but not on a team. <br>"
                       f"Your submission was not recorded, but the response would have been: \"{s.response_text}\"")
        form.errors['answer'] = [err_message]
        return HttpResponse(render_crispy_form(form))

    s.save()
    if s.is_correct:
        PuzzleStatus.objects.get(puzzle=puzzle, team=team).mark_solved()

    form = AnswerForm(puzzle=puzzle, disable_form=s.is_correct)
    return HttpResponse(render_crispy_form(form))


def puzzle_hints_view(request, pk):
    puzzle = get_object_or_404(Puzzle, pk=pk)
    team = puzzle.hunt.team_from_user(request.user)
    if not team.hints_open_for_puzzle(puzzle):
        render(request, 'access_error.html', {'reason': "hint"})
    hints = Hint.objects.filter(team=team, puzzle=puzzle).order_by("-pk")
    context = {"puzzle": puzzle, "team": team, "hints": hints}
    return render(request, "puzzle_hints.html", context)


def puzzle_hints_submit(request, pk):
    if "hintText" not in request.POST:
        raise SuspiciousOperation
    puzzle = get_object_or_404(Puzzle, pk=pk)
    team = puzzle.hunt.team_from_user(request.user)
    if not team.hints_open_for_puzzle(puzzle) or team.num_available_hints <= 0:
        render(request, 'access_error.html', {'reason': "hint"})

    Hint.objects.create(puzzle=puzzle, team=team, request=request.POST.get("hintText"),
                        request_time=timezone.now(), last_modified_time=timezone.now())
    return redirect("puzzlehunt:puzzle_hints_view", pk)


def hunt_view(request, hunt):
    """
    The main view to render hunt templates. Does various permission checks to determine the set
    of puzzles to display and then renders the string in the hunt's "template" field to HTML.
    """

    team = hunt.team_from_user(request.user)
    puzzle_list = []

    # TODO: consider moving the puzzle list logic to the model.
    # Admins get all access, wrong teams/early lookers get an error page
    # real teams get appropriate puzzles, and puzzles from past hunts are public
    if hunt.is_public or request.user.is_staff:
        puzzle_list = hunt.puzzle_set.all()

    elif team and team.playtest_happening:
        puzzle_list = team.puzzle_statuses.all()

    # Hunt has not yet started
    elif hunt.is_locked:
        # TODO: This is rather prescriptive behavior, consider changing
        if hunt.is_day_of_hunt:
            return render(request, 'access_error.html', {'reason': "hunt"})
        else:
            return hunt_prepuzzle(request, hunt.id)

    # Hunt has started
    elif hunt.is_open:
        # see if the team does not belong to the hunt being accessed
        if not request.user.is_authenticated:
            return redirect('%s?next=%s' % (reverse_lazy(settings.LOGIN_URL), request.path))

        elif team is None or (team.hunt != hunt):
            return render(request, 'access_error.html', {'reason': "team"})
        else:
            puzzle_list = team.puzzle_statuses.all()


    # No else case, all 3 possible hunt states have been checked.

    puzzles = sorted(puzzle_list, key=lambda p: p.order_number)
    if team is None:
        solved = []
    else:
        solved = team.puzzle_statuses.filter(puzzlestatus__solve_time__isnull=False)
    context = {'hunt': hunt, 'puzzles': puzzles, 'team': team, 'solved': solved}

    if hunt.template_file is None or hunt.template_file == "":
        return render(request, 'hunt_non_template.html', context)
    else:
        return render(request, f"hunt/{hunt.pk}/template.html", context)


def hunt_leaderboard(request, hunt):
    ruleset = hunt.teamrankingrule_set.order_by("rule_order").all()

    teams = hunt.team_set.exclude(playtester=True)
    for rule in ruleset:
        teams = rule.annotate_query(teams)

    teams = teams.order_by(*[rule.ordering_parameter for rule in ruleset]).all()

    return render(request, 'leaderboard.html', {'team_data': teams, 'ruleset': ruleset, 'hunt': hunt})


def hunt_updates(request, hunt):
    updates = hunt.update_set.all().order_by('time')
    return render(request, "updates.html", {"updates": updates})


def hunt_info(request, hunt):
    context = {'hunt': hunt}

    if hunt.info_page_file is None or hunt.info_page_file == "":
        return render(request, 'hunt_info_non_template.html', context)
    else:
        return render(request, f"hunt/{hunt.pk}/info_page.html", context)


def hunt_prepuzzle(request, hunt):
    """
    A simple view that locates the correct prepuzzle for a hunt and redirects there if it exists.
    """

    if hasattr(hunt, "prepuzzle"):
        return prepuzzle_view(request, hunt.prepuzzle.pk)
    else:
        # Maybe we can do something better, but for now, redirect to the main page
        return redirect('puzzlehunt:hunt_info', hunt.pk)


# TODO: if we ever allow the main pages to require javascript, this can go away and the submit method can just use htmx
def render_prepuzzle(request, form, puzzle, submission=None):
    context = {'form': form, 'puzzle': puzzle, 'submission': submission}
    if puzzle.main_file is None or not puzzle.main_file.extension == "tmpl":
        return render(request, "prepuzzle_non_template.html", context)
    else:
        return render(request, puzzle.main_file.file.name.removeprefix("trusted/"), context)


def prepuzzle_view(request, pk):
    # """
    # A view to handle answer submissions via POST and render the prepuzzle's template.
    # """

    puzzle = Prepuzzle.objects.get(pk=pk)

    if not (puzzle.released or request.user.is_staff):
        return redirect('puzzlehunt:hunt_info', "current")
    form = AnswerForm(puzzle=puzzle, is_prepuzzle=True)
    return render_prepuzzle(request, form, puzzle)


# TODO: This view feels way too manual, maybe we should pull some of this out into the prepuzzle model.
def check_prepuzzle_answer(request, pk):
    puzzle = get_object_or_404(Prepuzzle, pk=pk)
    # You must have access to the hunt and the puzzle to make a submission
    if not (puzzle.check_access(request.user)):
        raise SuspiciousOperation

    # Get submission and respond to it here
    form = AnswerForm(request.POST, puzzle=puzzle, is_prepuzzle=True)
    if not form.is_valid():
        if request.htmx:
            return HttpResponse(render_crispy_form(form))
        return render_prepuzzle(request, form, puzzle)

    user_answer = form.cleaned_data['answer']
    if puzzle.case_sensitive:
        is_correct = user_answer == puzzle.answer
    else:
        is_correct = user_answer.lower() == puzzle.answer.lower()

    if is_correct:
        if puzzle.response_string is not None and puzzle.response_string != "":
            response_text = puzzle.response_string
        else:
            response_text = "Correct"
    else:
        response_text = "Wrong Answer."
    
    return is_correct, response_text


def prepuzzle_submit(request, pk):
    puzzle = get_object_or_404(Prepuzzle, pk=pk)
    is_correct, response_text = check_prepuzzle_answer(request, pk)
    s = {'is_correct': is_correct, 'response_text': response_text} # God I hate duck typing

    if request.htmx:
        response = render(request, "partials/_puzzle_public_response.html", context={'submission': s})
        return retarget(reswap(response, "outerHTML"), "#public-answer-status")
    form = AnswerForm(puzzle=puzzle, is_prepuzzle=True, disable_form=is_correct)
    return render_prepuzzle(request, form, puzzle, s)


# Legacy view for old prepuzzles
def prepuzzle_check(request, pk):
    is_correct, response_text = check_prepuzzle_answer(request, pk)
    if not is_correct:
        response_text = ""
    return JsonResponse({'is_correct': is_correct, 'response': response_text})