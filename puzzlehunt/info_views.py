from django_ratelimit.decorators import ratelimit

from django.shortcuts import render, get_object_or_404, redirect
from django.http import QueryDict
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages

from .models import Hunt, Team, DisplayOnlyHunt, NotificationSubscription, Event
from .forms import TeamForm, UserEditForm, NotificationSubscriptionForm


@require_GET
def index(request):
    """ Main landing page view, mostly static except for hunt info """
    curr_hunt = Hunt.objects.get(is_current_hunt=True)
    return render(request, "index.html", {'curr_hunt': curr_hunt})


@require_GET
def archive(request):
    """ A view to render the list of previous hunts, will show any hunt that is 'public' """
    normal_hunts = [hunt for hunt in Hunt.objects.all() if hunt.is_public]
    display_only_hunts = DisplayOnlyHunt.objects.all()

    for hunt in normal_hunts:
        hunt.num_teams = hunt.team_set.count()
        hunt.num_puzzles = hunt.puzzle_set.count()

    all_hunts = list(normal_hunts) + list(display_only_hunts)
    all_hunts.sort(key=lambda x: x.display_start_date)

    return render(request, "archive.html", {'hunts': all_hunts})


@login_required
def user_detail_view(request):
    if request.method == "GET":
        user_form = UserEditForm(instance=request.user)
        return render(request, "user_detail.html", {'user_form': user_form})
    elif request.method == "PATCH":
        data = QueryDict(request.body)

        user_form = UserEditForm(data, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "User details changed successfully.")

        if request.htmx:
            return render(request, "partials/_message_update_user_form.html", {'user_form': user_form})
        else:
            return redirect("puzzlehunt:user_detail_view")


@require_GET
@login_required
def team_view(request, pk):
    current_team = Hunt.objects.get(is_current_hunt=True).team_from_user(request.user)
    if pk == "current":
        team = current_team
    else:
        team = get_object_or_404(Team, pk=pk)
    
    if team is not None and not (request.user.is_staff or request.user in team.members.all()):
        raise PermissionDenied

    teams = request.user.team_set.order_by("-hunt__start_date")

    form = None
    if team is not None:
        form = TeamForm(instance=team)

    context = {'team': team, 'form': form, 'teams': teams, 'current_team': current_team}

    return render(request, "team_detail.html", context)


@require_POST
@login_required
def team_update(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if not (request.user.is_staff or request.user in team.members.all()):
        raise PermissionDenied

    team_form = TeamForm(request.POST, instance=team)
    if team_form.is_valid():
        team_form.save()
        messages.success(request, "Team details changed succesfully.")
    else:
        if not request.htmx:
            messages.warning(request, team_form.errors['name'])

    if request.htmx:
        return render(request, "partials/_team_name_and_form.html", {'team': team, 'form': team_form})
    else:
        return redirect("puzzlehunt:team_view", team.pk)


@require_http_methods(['GET', 'POST'])
@login_required
def team_create(request):
    """
    The view that handles team registration. Mostly deals with creating the team object from the post request.
    """

    current_hunt = Hunt.objects.get(is_current_hunt=True)
    team = current_hunt.team_from_user(request.user)
    if team:
        return redirect('puzzlehunt:team_view', 'current')

    if request.method == 'POST':
        team_form = TeamForm(request.POST, instance=Team(hunt=current_hunt))
        if team_form.is_valid():
            team = team_form.save()
            team.members.add(request.user)
            Event.objects.create_event(Event.EventType.TEAM_JOIN, team, user=request.user)

            messages.success(request, f"You have joined {team.name}")
            return redirect('puzzlehunt:team_view', 'current')
    else:
        team_form = TeamForm()

    return render(request, "team_registration.html", {'form': team_form})


@require_GET
@login_required
@ratelimit(key='user', rate='6/m')
def team_join(request, pk=None):
    join_code = request.GET.get("code", "")
    if not join_code:
        error = "Join code cannot be empty."
        return render(request, "team_registration.html", {"form": TeamForm(), 'errors': error})

    if pk is None:
        current_hunt = Hunt.objects.get(is_current_hunt=True)
        current_team = current_hunt.team_from_user(request.user)
        if current_team:
            return redirect('puzzlehunt:team_view', current_team.pk)

        try:
            team = current_hunt.team_set.get(join_code=join_code.upper())
        except Team.DoesNotExist:
            error = "No team with that join code exists."
            return render(request, "team_registration.html", {"form": TeamForm(), 'errors': error})
    else:
        team = get_object_or_404(Team, pk=pk)
        possible_current_team = team.hunt.team_from_user(request.user)
        if possible_current_team:
            return redirect('puzzlehunt:team_view', possible_current_team.pk)

        if team.join_code != join_code:
            raise PermissionDenied

    messages.success(request, f"You have joined {team.name}")
    team.members.add(request.user)
    return redirect('puzzlehunt:team_view', team.pk)


@require_POST
@login_required
def team_leave(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if not request.user in team.members.all():
        raise PermissionDenied

    team.members.remove(request.user)
    if team.members.count() == 0:
        team.delete()
    messages.success(request, f"You have left team {team.name}")
    return redirect('puzzlehunt:team_view', 'current')


@login_required
def notification_view(request):
    form = None
    if request.method == "GET":
        form = NotificationSubscriptionForm()
    elif request.method == "POST":
        form = NotificationSubscriptionForm(request.POST)
        form.instance.user = request.user

        if form.is_valid():
            form.save()
            form = NotificationSubscriptionForm()
            messages.success(request, "Notification settings updated successfully.")

    subscriptions = NotificationSubscription.objects.filter(user=request.user).select_related('platform', 'hunt')
    
    # Add event type choices for display
    event_type_choices = [(et.value, et.label) for et in Event.EventType]

    context = {
        'subscriptions': subscriptions,
        'form': form,
        'event_type_choices': event_type_choices
    }

    if request.htmx:
        return render(request, "partials/_notification_table_and_form.html", context)
    else:
        return render(request, "notification_detail.html", context)


@login_required
@require_http_methods(["DELETE"])
def notification_delete(request, pk):
    subscription = get_object_or_404(NotificationSubscription, pk=pk)
    if not (request.user.is_staff or request.user == subscription.user):
        raise PermissionDenied

    subscription.delete()
    messages.success(request, "Notification subscription deleted.")
    
    if request.htmx:
        subscriptions = NotificationSubscription.objects.filter(user=request.user).select_related('platform', 'hunt')
        event_type_choices = [(et.value, et.label) for et in Event.EventType]
        return render(request, "notification_table.html", 
                      {'subscriptions': subscriptions, 'event_type_choices': event_type_choices})
    return redirect("puzzlehunt:notification_view")


@login_required
@require_POST
def notification_toggle(request, pk):
    subscription = get_object_or_404(NotificationSubscription, pk=pk)
    if not (request.user.is_staff or request.user == subscription.user):
        raise PermissionDenied

    subscription.active = not subscription.active
    subscription.save()
    
    if request.htmx:
        return render(request, "partials/_notification_active_toggle.html", {'subscription': subscription})
    return redirect("puzzlehunt:notification_view")
