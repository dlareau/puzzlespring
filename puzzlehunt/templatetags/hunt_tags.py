from django import template
from django.conf import settings
from django.template import Template, Context
from django.urls import reverse
from puzzlehunt.models import Hunt, Prepuzzle
from constance import config
from urllib.parse import urlparse

register = template.Library()


@register.simple_tag(takes_context=True)
def hunt_static(context):
    return settings.PROTECTED_URL + "hunt/" + str(context['hunt'].id) + "/files/"


@register.simple_tag(takes_context=True)
def prepuzzle_static(context):
    from django.conf import settings
    return settings.PROTECTED_URL + "prepuzzle/" + str(context['puzzle'].pk) + "/files/"


@register.simple_tag()
def site_title():
    return config.SITE_TITLE


@register.simple_tag()
def contact_email():
    return config.CONTACT_EMAIL


@register.simple_tag()
def embed_image():
    if config.EMBED_IMAGE:
        return f"{settings.MEDIA_URL}{config.EMBED_IMAGE}"
    return settings.STATIC_URL + "puzzlehunt/embed_logo.jpg"


@register.simple_tag()
def navbar_image():
    if config.NAVBAR_IMAGE:
        return f"{settings.MEDIA_URL}{config.NAVBAR_IMAGE}"
    return settings.STATIC_URL + "puzzlehunt/navbar_logo.png"


@register.simple_tag()
def favicon():
    if config.FAVICON:
        return f"{settings.MEDIA_URL}{config.FAVICON}"
    return settings.STATIC_URL + "puzzlehunt/favicon.ico"


@register.filter()
def render_with_context(value):
    return Template(value).render(Context({'curr_hunt': Hunt.objects.get(is_current_hunt=True)}))


@register.tag
def set_curr_team(parser, token):
    return CurrentTeamEventNode()


class CurrentTeamEventNode(template.Node):
    def render(self, context):
        context['current_hunt_team'] = Hunt.objects.get(is_current_hunt=True).team_from_user(context['request'].user)
        return ''


@register.tag
def set_all_hunts(parser, token):
    return AllHuntsEventNode()


class AllHuntsEventNode(template.Node):
    def render(self, context):
        old_hunts = Hunt.objects.all()
        context['tmpl_all_hunts'] = old_hunts.order_by("-id")
        return ''


@register.tag
def set_hunt_from_context(parser, token):
    return HuntFromContextEventNode()


class HuntFromContextEventNode(template.Node):
    def render(self, context):
        if "hunt" in context:
            context['tmpl_hunt'] = context['hunt']
            return ''
        elif "puzzle" in context:
            context['tmpl_hunt'] = context['puzzle'].hunt
            return ''
        else:
            context['tmpl_hunt'] = Hunt.objects.get(is_current_hunt=True)
            return ''


@register.simple_tag()
def show_hints_link(team, puzzle):
    """
    Returns True if the hunt is public and the puzzle has any canned hints,
    OR if the team is allowed to view/request hints for the puzzle (normal logic).
    """
    if puzzle is None:
        return False
    # First, check if hunt is public and puzzle has canned hints (works even if team is None)
    if puzzle.hunt.is_public and puzzle.cannedhint_set.exists():
        return True
    # Normal logic, requires a team
    if team is None:
        return False
    if team.hints_open_for_puzzle(puzzle):
        return True
    return False


@register.simple_tag()
def get_attribute(obj, attribute):
    val = getattr(obj, attribute)
    if val is None:
        val = 0
    return val


@register.simple_tag
def active_page(request, view_name):
    from django.urls import resolve, Resolver404
    if not request:
        return ""
    try:
        r = resolve(request.path_info)
        url_name_bool = r.url_name == view_name
        if "url" in r.kwargs:
            url_val_bool = view_name.strip("/") in r.kwargs["url"]
        else:
            url_val_bool = False
        return "is-active" if (url_name_bool or url_val_bool) else ""
    except Resolver404:
        return ""


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    query = context['request'].GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()


@register.simple_tag(takes_context=True)
def is_prepuzzle(context, **kwargs):
    puzzle = context['puzzle']
    return isinstance(puzzle, Prepuzzle)


@register.filter()
def smooth_timedelta(timedeltaobj):
    """Convert a datetime.timedelta object into Days, Hours, Minutes, Seconds."""
    if not timedeltaobj:
        return ""
    secs = timedeltaobj.total_seconds()
    timetot = ""
    if secs > 86400: # 60sec * 60min * 24hrs
        days = secs // 86400
        timetot += "{} d".format(int(days))
        secs = secs - days*86400

    if secs > 3600:
        hrs = secs // 3600
        timetot += " {} h".format(int(hrs))
        secs = secs - hrs*3600

    if secs > 60:
        mins = secs // 60
        timetot += " {} m".format(int(mins))
    return timetot


@register.filter
def get_files(value, media_file_type):
    if media_file_type == "solution":
        return value.solution_files.all()
    else:
        return value.files.all()


@register.filter
def order_number_exists(value, number):
    if value is None:
        return False
    return any([x.order_number == number for x in value])


@register.simple_tag
def email_backend_configured():
    """Check if an email backend is configured in settings."""
    return bool(settings.EMAIL_CONFIGURED)


@register.simple_tag(takes_context=True)
def hunt_back_url(context, hunt_pk):
    """
    Returns the back URL for a hunt page, using HTTP_REFERER if it's a valid hunt_view URL
    for the specified hunt, otherwise returns the default hunt_view URL.
    """
    request = context.get('request')
    if not request:
        return reverse('puzzlehunt:hunt_view', args=[hunt_pk])
    
    referer = request.META.get('HTTP_REFERER')
    if not referer:
        return reverse('puzzlehunt:hunt_view', args=[hunt_pk])
    
    # Check if referer is a hunt_view URL for the correct hunt
    parsed = urlparse(referer)
    expected_path = f'/hunt/{hunt_pk}/view/'
    if parsed.path.startswith(expected_path):
        return referer
    
    return reverse('puzzlehunt:hunt_view', args=[hunt_pk])