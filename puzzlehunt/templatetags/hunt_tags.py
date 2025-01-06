from django import template
from django.conf import settings
from django.template import Template, Context
from puzzlehunt.models import Hunt, TeamRankingRule, Prepuzzle
from datetime import datetime, timedelta
from constance import config
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
    return settings.SITE_TITLE


@register.simple_tag()
def contact_email():
    return config.CONTACT_EMAIL


@register.filter
def strip_andrew(value):
    if "@" in value:
        vals = value.split("@")
        if vals[1] == "andrew.cmu.edu":
            return f"{vals[0]}@andrew"
    return value


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


# TODO: Determine if these three tags are actually used after the refactor
@register.tag
def set_curr_hunt(parser, token):
    return CurrentHuntEventNode()


class CurrentHuntEventNode(template.Node):
    def render(self, context):
        try:
            context['tmpl_curr_hunt'] = Hunt.objects.get(is_current_hunt=True)
        except:
            pass
        return ''


@register.tag
def set_recent_hunts(parser, token):
    return RecentHuntsEventNode()


class RecentHuntsEventNode(template.Node):
    def render(self, context):
        old_hunts = Hunt.objects.filter(end_date__lt=datetime.now()).exclude(is_current_hunt=True)
        context['tmpl_recent_hunts'] = old_hunts.order_by("-id")[:5]
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
def hints_open(team, puzzle):
    if team is None or puzzle is None:
        return False
    return team.hints_open_for_puzzle(puzzle)


@register.simple_tag()
def get_attribute(obj, attribute):
    val = getattr(obj, attribute)
    if val is None:
        val = 0
    return val


@register.simple_tag(takes_context=True)
def shib_login_url(context, entityID, next_path):
    if context['request'].is_secure():
        protocol = "https://"
    else:
        protocol = "http://"
    shib_str = "https://" + settings.SHIB_DOMAIN + "/Shibboleth.sso/Login"
    entity_str = "entityID=" + entityID
    target_str = "target=" + protocol + context['request'].get_host() + "/shib/login"
    next_str = "next=" + next_path

    return shib_str + "?" + entity_str + "&" + target_str + "?" + next_str


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

@register.filter
def hours(value):
    return (abs(value).days * 24) + (abs(value).seconds // 3600)

@register.filter
def hours_and_minutes(value):
    return ":".join(str(value + timedelta(minutes=1)).split(":")[:-1])

@register.filter()
def smooth_timedelta(timedeltaobj):
    """Convert a datetime.timedelta object into Days, Hours, Minutes, Seconds."""
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
def progress_table_color(status):
    if status is None:
        return ""
    if status.solve_time:
        return "background-color: #aaffaa;"
    time_since_hours = hours(status.time_since)
    if time_since_hours > 5:
        return "background-color: #ff9999;"
    if time_since_hours > 3:
        return "background-color: #ffbbaa;"
    if time_since_hours > 1:
        return "background-color: #ffddaa;"
    if status.unlock_time:
        return "background-color: #ffffaa;"
    return ""

@register.filter
def progress_table_border(status):
    if status is None or not hasattr(status, "num_hints"):
        return "padding: 4px;"  # Match border width
    if status.num_hints == 1:
        return "border: 4px solid #ffdb26;"
    if status.num_hints == 2:
        return "border: 4px solid #db5100;"
    if status.num_hints >= 3:
        return "border: 4px solid #000000;"
    return "padding: 4px;"  # Match border width

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