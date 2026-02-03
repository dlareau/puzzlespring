import re

from django.contrib.auth.base_user import BaseUserManager
from django.db import models, transaction
from dateutil import tz
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import logging
import os
import random
import json
from constance import config
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property

from django.db.models import F, OuterRef, Count, Subquery, Max, Avg, Q
from django.db.models.fields import PositiveIntegerField, DateTimeField, DurationField
from django.db.models.functions import Lower
from django.db.models.signals import m2m_changed
from django.utils import timezone
from django_eventstream import send_event
from .config_parser import parse_config, process_config_rules

logger = logging.getLogger(__name__)

time_zone = tz.gettz(settings.TIME_ZONE)


def send_event_to_team_members(team, event_name, data):
    """Send an SSE event to all members of a team via their user channels."""
    for member_pk in team.members.values_list('pk', flat=True):
        send_event(f"user-{member_pk}", event_name, data)

# region User Model
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=40, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def full_name(self):
        name = self.first_name + " " + self.last_name
        if name == " ":
            return "Anonymous User"
        else:
            return name

    def display_string(self):
        return self.display_name if self.display_name else self.email

    def __str__(self):
        return f"{self.display_string()} - {self.full_name()}"

    def save(self, *args, **kwargs):
        is_new = not bool(self.pk)
        super().save(*args, **kwargs)
        if is_new:
            self._create_browser_subscription()

    def _create_browser_subscription(self):
        """Create default browser notification subscription for new users."""
        browser_platform = NotificationPlatform.objects.filter(
            type=NotificationPlatform.PlatformType.BROWSER,
            enabled=True
        ).first()
        if browser_platform:
            event_types = ','.join([
                Event.EventType.PUZZLE_SOLVE,
                Event.EventType.PUZZLE_UNLOCK,
                Event.EventType.HINT_RESPONSE,
                Event.EventType.HINT_REFUND,
            ])
            NotificationSubscription.objects.create(
                user=self,
                platform=browser_platform,
                event_types=event_types,
                active=True
            )

# endregion


# region Media File Models
class OverwriteStorage(FileSystemStorage):
    """ A custom storage class that just overwrites existing files rather than erroring """

    def get_available_name(self, name, max_length=None):
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

    def url(self, name):
        return settings.PROTECTED_URL + name
    
    def _save(self, name, content):
        result = super(OverwriteStorage, self)._save(name, content)
        if name.endswith('.tmpl') or name.endswith('.html'):
            from puzzlehunt.utils import invalidate_template_cache
            template_path = name.removeprefix("trusted/")
            invalidate_template_cache(template_path)
        return result
        


def get_media_file_path(instance, filename):
    return f"trusted/{instance.save_path}/{instance.parent.pk}/files/{filename}"


class MediaFileManager(models.Manager):
    def get_by_natural_key(self, *args):
        # The last argument is always the relative_name
        relative_name = args[-1]
        parent_natural_key = args[:-1]
        
        # Check if the parent model is Puzzle, matching natural_key logic
        parent_model = self.model.parent.field.related_model
        if parent_model == Puzzle:
            puzzle_id = parent_natural_key[0]
            return self.get(parent_id=puzzle_id, file__endswith=relative_name)
        
        # For other file types, find the parent using its natural key
        parent = parent_model.objects.get_by_natural_key(*parent_natural_key)
        return self.get(parent=parent, file__endswith=relative_name)


class MediaFile(models.Model):
    file = models.FileField(
        upload_to=get_media_file_path,
        storage=OverwriteStorage(),
        unique=True,
    )

    objects = MediaFileManager()

    class Meta:
        abstract = True

    def check_access(self, user):
        # Implemented by child classes
        raise NotImplementedError

    @property
    def relative_name(self):
        return "/".join(self.file.name.split("/")[4:])

    @property
    def extension(self):
        return self.file.name.split(".")[-1]

    @property
    def is_text_editable(self):
        TEXT_EXTENSIONS = {'.html', '.htm', '.css', '.js', '.txt', '.tmpl'}
        from pathlib import Path
        return Path(self.file.name).suffix.lower() in TEXT_EXTENSIONS

    def __str__(self):
        return self.file.name.removeprefix("trusted/")

    def natural_key(self):
        if isinstance(self.parent, Puzzle):
            return (self.parent.id, self.relative_name)
        return self.parent.natural_key() + (self.relative_name,)

# We are purposefully choosing to have inherited models over a generic relation
class PuzzleFile(MediaFile):
    save_path = "puzzle"
    parent = models.ForeignKey("Puzzle", related_name="files", on_delete=models.CASCADE)

    def check_access(self, user):
        return self.parent.hunt.check_access(user) and self.parent.check_access(user)


class SolutionFile(MediaFile):
    save_path = "solution"
    parent = models.ForeignKey("Puzzle", related_name="solution_files", on_delete=models.CASCADE)

    def check_access(self, user):
        return self.parent.hunt.check_access(user) and self.parent.check_access(user, solution=True)


class HuntFile(MediaFile):
    save_path = "hunt"
    parent = models.ForeignKey("Hunt", related_name="files", on_delete=models.CASCADE)

    def check_access(self, user):
        return self.parent.check_access(user)


class PrepuzzleFile(MediaFile):
    save_path = "prepuzzle"
    parent = models.ForeignKey("Prepuzzle", related_name="files", on_delete=models.CASCADE)

    def check_access(self, user):
        return self.parent.check_access(user)
# endregion


# region Hunt Model
def get_hunt_template_path(instance, filename):
    return f"trusted/hunt/{instance.pk}/template.html"

def get_hunt_info_page_path(instance, filename):
    return f"trusted/hunt/{instance.pk}/info_page.html"


class HuntManager(models.Manager):
    def get_by_natural_key(self, name, start_date):
        return self.get(name=name, start_date=start_date)


class Hunt(models.Model):
    """ Base class for a hunt. Contains basic details about a puzzlehunt. """

    objects = HuntManager()

    name = models.CharField(
        max_length=200,
        help_text="The name of the hunt as the public will see it")
    team_size_limit = models.IntegerField()
    start_date = models.DateTimeField(
        help_text="The date/time at which a hunt will become visible to registered users")
    end_date = models.DateTimeField(
        help_text="The date/time at which a hunt will be archived and available to the public")
    display_start_date = models.DateTimeField(
        help_text="The start date/time displayed to users")
    display_end_date = models.DateTimeField(
        help_text="The end date/time displayed to users")
    location = models.CharField(
        blank=True,
        max_length=100,
        help_text="Starting location of the puzzlehunt")
    is_current_hunt = models.BooleanField(
        default=False)
    template_file = models.FileField(
        upload_to=get_hunt_template_path,
        storage=OverwriteStorage(),
        blank=True,
        null=True,
    )
    info_page_file = models.FileField(
        upload_to=get_hunt_info_page_path,
        storage=OverwriteStorage(),
        blank=True,
        null=True,
    )
    hint_lockout = models.IntegerField(
        help_text="Time (in minutes) teams must wait before a hint can be used on a newly unlocked puzzle",
        default=60  # Default 60 minute lockout
    )
    css_file = models.ForeignKey(
        HuntFile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    config = models.TextField(
        blank=True,
        help_text="Configuration for puzzle, point and hint unlocking rules"
    )
    ratelimit_override = models.CharField(
        max_length=20,
        help_text="Override default answer submission rate limit (format: X/YZ, e.g. 3/5m)",
        blank=True,
        null=True,
        default=""
    )

    # This is set automatically by the config parser
    class HintPoolType(models.TextChoices):
        GLOBAL_ONLY = 'GLOBAL', 'Global hint pool only'
        PUZZLE_ONLY = 'PUZZLE', 'Puzzle-specific hints only'
        BOTH_POOLS = 'BOTH', 'Both global and puzzle-specific hints'
    
    class CannedHintPolicy(models.TextChoices):
        CANNED_ONLY = 'ONLY', 'Only canned hints allowed (no custom hints)'
        CANNED_FIRST = 'FIRST', 'Canned hints must be used before custom hints'
        MIXED = 'MIXED', 'Canned and custom hints can be used in any order'
    
    class HintPoolAllocation(models.TextChoices):
        PUZZLE_PRIORITY = 'PUZZ', 'Use puzzle-specific hints before global hints'
        HINT_TYPE_SPLIT = 'SPLIT', 'Canned hints use puzzle pool, custom hints use global pool'

    hint_pool_type = models.CharField(
        max_length=6,
        choices=HintPoolType.choices,
        default=HintPoolType.GLOBAL_ONLY,
        help_text="Which hint pools are available in this hunt"
    )
    
    canned_hint_policy = models.CharField(
        max_length=5,
        choices=CannedHintPolicy.choices,
        default=CannedHintPolicy.CANNED_FIRST,
        help_text="How canned hints interact with custom hints"
    )
    
    hint_pool_allocation = models.CharField(
        max_length=5,
        choices=HintPoolAllocation.choices,
        default=HintPoolAllocation.PUZZLE_PRIORITY,
        help_text="How hints are allocated between puzzle and global pools when both exist"
    )

    @property
    def is_locked(self):
        """ A boolean indicating whether the hunt is locked """
        return timezone.now() < self.start_date

    @property
    def is_open(self):
        """ A boolean indicating whether the hunt is open to registered participants """
        return self.start_date <= timezone.now() < self.end_date

    @property
    def is_public(self):
        """ A boolean indicating whether the hunt is open to the public """
        return timezone.now() > self.end_date

    @property
    def is_day_of_hunt(self):
        """ A boolean indicating whether today is the day of the hunt """
        return timezone.now().date() == self.start_date.date()

    @property
    def teams(self):
        """ Gets the teams for the hunt sorted alphabetically. """
        return self.team_set.order_by(Lower("name")).all()
    
    @property
    def active_teams(self):
        """ Gets the teams that are currently playing or have played the hunt """
        if self.is_public or self.is_open:
            return self.team_set.exclude(playtester=True)
        else:
            return self.team_set.filter(playtester=True)
        
    @property
    def no_team_mode(self):
        """ A boolean indicating whether the hunt is in no team mode """
        return self.team_size_limit == 1

    def __str__(self):
        if self.is_current_hunt:
            return self.name + " (c)"
        else:
            return self.name

    def clean(self):
        """ Validates the hunt model """
        if not self.is_current_hunt:
            try:
                old_obj = Hunt.objects.get(pk=self.pk)
                if old_obj.is_current_hunt:
                    raise ValidationError({'is_current_hunt':
                                        ["There must always be one current hunt", ]})
            except ObjectDoesNotExist:
                pass
        if self.pk and self.config:
            try:
                puzzles = self.puzzle_set.values_list('id', 'order_number')
                puzzle_ids = set(p[0] for p in puzzles)
                order_to_id = {p[1]: p[0] for p in puzzles}
                parse_config(self.config, puzzle_ids, order_to_id)
            except Exception as e:
                raise ValidationError({'config': [str(e)]})

        super(Hunt, self).clean()

    @transaction.atomic
    def save(self, *args, **kwargs):
        """ Overrides the standard save method to ensure that only one hunt is the current hunt """
        self.full_clean()
        if self.is_current_hunt:
            Hunt.objects.filter(is_current_hunt=True).update(is_current_hunt=False)
        super(Hunt, self).save(*args, **kwargs)

    def team_from_user(self, user):
        """ Takes a user and a hunt and returns either the user's team for that hunt or None """
        if not user.is_authenticated:
            return None
        teams = user.team_set.filter(hunt=self)
        return teams[0] if (len(teams) > 0) else None

    def check_access(self, user):
        if self.is_public or user.is_staff:
            return True
        team = self.team_from_user(user)
        if team is not None and (self.is_open or team.playtest_happening):
            return True
        return False

    def natural_key(self):
        return (self.name, self.start_date)
    
    def reset(self):
        PuzzleStatus.objects.filter(team__hunt=self).delete()
        Submission.objects.filter(puzzle__hunt=self).delete()
        Hint.objects.filter(puzzle__hunt=self).delete()
        self.update_set.all().delete()
        self.event_set.all().delete()

# endregion


class Puzzle(models.Model):
    """ A class representing a puzzle within a hunt """

    class Meta:
        ordering = ['-hunt', 'order_number']
        unique_together = [['hunt', 'order_number']]

    class PuzzleType(models.TextChoices):
        STANDARD_PUZZLE = 'STD', 'Standard'
        META_PUZZLE = 'MET', 'Meta'
        FINAL_PUZZLE = 'FIN', 'Final'
        NON_PUZZLE = 'NON', 'Non-puzzle'

    id = models.CharField(
        primary_key=True,
        max_length=8,
        unique=True,  # hex only please
        help_text="A 3-8 character hex string that uniquely identifies the puzzle")
    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that this puzzle is a part of")
    name = models.CharField(
        max_length=200,
        help_text="The name of the puzzle as it will be seen by hunt participants")
    order_number = models.IntegerField(
        help_text="The number of the puzzle within the hunt, for sorting purposes")
    answer = models.CharField(
        max_length=100,
        help_text="The answer to the puzzle.")
    type = models.CharField(
        max_length=3,
        choices=PuzzleType.choices,
        default=PuzzleType.STANDARD_PUZZLE,
        blank=False,
        help_text="The type of puzzle")
    extra_data = models.CharField(
        max_length=200,
        blank=True,
        help_text="A misc. field for any extra data to be stored with the puzzle.")
    allow_spaces = models.BooleanField(
        default=False,
        help_text="Allow spaces in the answer submissions")
    case_sensitive = models.BooleanField(
        default=False,
        help_text="Check for case in answer submissions")
    allow_non_alphanumeric = models.BooleanField(
        default=False,
        help_text="Allow for full unicode in answer submissions (rather than just A-Z and 0-9)")
    main_file = models.ForeignKey(
        PuzzleFile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    main_solution_file = models.ForeignKey(
        SolutionFile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    ratelimit_override = models.CharField(
        max_length=20,
        help_text="Override hunt's rate limit (format: X/YZ, e.g. 3/5m)",
        blank=True,
        null=True,
        default=""
    )

    @property
    def abbreviation(self):
        return "".join([w[0] for w in self.name.split(" ")])

    @property
    def safe_name(self):
        name = self.name.lower().replace(" ", "_")
        return re.sub(r'[^a-z_]', '', name)

    @property
    def solve_count(self):
        return PuzzleStatus.objects.filter(puzzle=self, solve_time__isnull=False).count()

    # Does not check for hunt access, so do that before calling this method
    def check_access(self, user, solution=False):
        if self.hunt.is_public or user.is_staff:
            return True
        team = self.hunt.team_from_user(user)
        if team is None:
            return False
        if solution:
            # TODO: Maybe there could be a settings boolean for if viewing solutions is allowed before/after the hunt is public
            return self in team.puzzle_statuses.filter(puzzlestatus__solve_time__isnull=False)
        else:
            return self in team.puzzle_statuses.filter(puzzlestatus__unlock_time__isnull=False)

    @classmethod
    def annotate_query(cls, query, annotation_type):
        match annotation_type:
            case 'num_hints':
                sq = Hint.objects.filter(puzzle__pk=OuterRef('pk'), team__playtester=False).order_by()
                sq = sq.values('puzzle').annotate(c=Count('*')).values('c')
                return query.annotate(num_hints=Subquery(sq, output_field=PositiveIntegerField()))
            case 'num_unlocks':
                sq = PuzzleStatus.objects.filter(puzzle__pk=OuterRef('pk'), unlock_time__isnull=False, team__playtester=False).order_by()
                sq = sq.values('puzzle').annotate(c=Count('*')).values('c')
                return query.annotate(num_unlocks=Subquery(sq, output_field=PositiveIntegerField()))
            case 'num_solves':
                sq = PuzzleStatus.objects.filter(puzzle__pk=OuterRef('pk'), solve_time__isnull=False, team__playtester=False).order_by()
                sq = sq.values('puzzle').annotate(c=Count('*')).values('c')
                return query.annotate(num_solves=Subquery(sq, output_field=PositiveIntegerField()))
            case 'num_submissions':
                sq = Submission.objects.filter(puzzle__pk=OuterRef('pk'), team__playtester=False).order_by()
                sq = sq.values('puzzle').annotate(c=Count('*')).values('c')
                return query.annotate(num_submissions=Subquery(sq, output_field=PositiveIntegerField()))
            case 'avg_solve_time':
                sq = PuzzleStatus.objects.filter(puzzle__pk=OuterRef('pk'), solve_time__isnull=False, team__playtester=False).order_by()
                sq = sq.values('puzzle').annotate(avg_time=Avg(F('solve_time') - F('unlock_time'))).values('avg_time')
                return query.annotate(avg_solve_time=Subquery(sq, output_field=DurationField()))

    def __str__(self):
        return f"{self.id} - {self.name}"


class PrepuzzleManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Prepuzzle(models.Model):
    """ A class representing a pre-puzzle within a hunt """

    objects = PrepuzzleManager()

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="The name of the puzzle as it will be seen by hunt participants")
    released = models.BooleanField(
        default=False)
    hunt = models.OneToOneField(
        Hunt,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="The hunt that this puzzle is a part of, leave blank for no associated hunt.")
    answer = models.CharField(
        max_length=100,
        help_text="The answer to the puzzle, not case sensitive")
    response_string = models.TextField(
        default="",
        blank=True,
        help_text="Data returned to the webpage for use upon solving.")
    allow_spaces = models.BooleanField(
        default=False,
        help_text="Allow spaces in the answer submissions")
    case_sensitive = models.BooleanField(
        default=False,
        help_text="Check for case in answer submissions")
    allow_non_alphanumeric = models.BooleanField(
        default=False,
        help_text="Allow for full unicode in answer submissions (rather than just A-Z and 0-9)")
    main_file = models.ForeignKey(
        PrepuzzleFile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    def __str__(self):
        if self.hunt:
            return "prepuzzle " + str(self.pk) + " (" + str(self.hunt.name) + ")"
        else:
            return "prepuzzle " + str(self.pk)

    def check_access(self, user):
        if user.is_staff:
            return True
        return self.released

    def natural_key(self):
        return (self.name,)

# region Team Model
def team_key_gen():
    join_code = "JOIN123"
    bad_code = True
    while bad_code:
        join_code = ''.join(random.choice("ACDEFGHJKMNPRSTUVWXYZ2345679") for _ in range(8))
        bad_code = Team.objects.filter(join_code=join_code).exists()
    return join_code


class TeamManager(models.Manager):
    def get_by_natural_key(self, join_code, hunt_name, hunt_start_date):
        return self.get(join_code=join_code, hunt__name=hunt_name, hunt__start_date=hunt_start_date)


class Team(models.Model):
    """ A class representing a team within a hunt """

    objects = TeamManager()

    name = models.CharField(
        verbose_name="Team Name",
        max_length=100,
        help_text="The team name as it will be shown to hunt participants")
    puzzle_statuses = models.ManyToManyField(
        Puzzle,
        blank=True,
        through="PuzzleStatus",
        help_text="The statuses of puzzles the team has unlocked")
    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that the team is a part of")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        help_text="Members of this team")
    custom_data = models.CharField(
        max_length=100,
        blank=True,
        help_text=f"A field for custom registration data"
    )
    join_code = models.CharField(
        max_length=8,
        default=team_key_gen,
        help_text="The 8 character random alphanumeric password needed for a user to join a team")
    playtester = models.BooleanField(
        default=False,
        help_text="A boolean to indicate if the team is a playtest team and will get early access")
    playtest_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date/time at which a hunt will become available to the playtesters")
    playtest_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date/time at which a hunt will no longer be available to playtesters")
    num_available_hints = models.IntegerField(
        default=0,
        help_text="The number of hints the team currently has available to use"
    )
    num_total_hints_earned = models.IntegerField(
        default=0,
        help_text="The total number of hints this team has earned through config rules"
    )
    points = models.IntegerField(
        default=0,
        help_text="The total number of points this team has earned through config rules"
    )
    badges = models.JSONField(default=list, help_text="List of badge texts earned by this team")

    @property
    def is_playtester_team(self):
        """ A boolean indicating whether the team is a playtesting team """
        return self.playtester

    @property
    def is_normal_team(self):
        """ A boolean indicating whether the team is a normal (non-playtester) team """
        return not self.playtester

    @property
    def playtest_started(self):
        """ A boolean indicating whether the team is currently allowed to be playtesting """
        if self.playtest_start_date is None or self.playtest_end_date is None:
            return False
        return self.playtester and timezone.now() >= self.playtest_start_date

    @property
    def playtest_over(self):
        """ A boolean indicating whether the team's playtest slot has passed """
        if self.playtest_start_date is None or self.playtest_end_date is None:
            return False
        return self.playtester and timezone.now() >= self.playtest_end_date

    @property
    def playtest_happening(self):
        """ A boolean indicating whether the team's playtest slot is currently happening """
        return self.playtest_started and not self.playtest_over

    @property
    def short_name(self):
        """ Team name shortened to 30 characters for more consistent display """
        if len(self.name) > 30:
            return self.name[:30] + "..."
        else:
            return self.name

    @property
    def size(self):
        """ The number of people on the team """
        return self.members.count()

    def solved_puzzles(self):
        """Get all solved puzzles for the team."""
        return Puzzle.objects.filter(puzzlestatus__team=self, puzzlestatus__solve_time__isnull=False)

    def unlocked_puzzles(self):
        """Get all unlocked puzzles for the team."""
        return Puzzle.objects.filter(puzzlestatus__team=self, puzzlestatus__unlock_time__isnull=False)

    def solved_metas(self):
        """Get all solved meta puzzles for the team."""
        return Puzzle.objects.filter(puzzlestatus__team=self, puzzlestatus__solve_time__isnull=False, type=Puzzle.PuzzleType.META_PUZZLE)

    def hints_open_for_puzzle(self, puzzle):
        """ Takes a puzzle and returns whether the team is allowed to view the hints page for that puzzle """    
        try:
            status = PuzzleStatus.objects.get(team=self, puzzle=puzzle)
        except PuzzleStatus.DoesNotExist:
            if self.hunt.is_public and puzzle.cannedhint_set.count() > 0:
                return True
            else:
                return False

        custom_open = self.num_custom_hint_requests_available(status) > 0
        canned_open = self.num_canned_hint_requests_available(status) > 0
        already_used_hints = self.hint_set.filter(puzzle=puzzle).count() > 0
        if custom_open or canned_open or already_used_hints:
            return (timezone.now() - status.unlock_time).total_seconds() > 60 * self.hunt.hint_lockout
        else:
            return False
        
    def num_custom_hint_requests_available(self, puzzle_status):
        """Returns the number of custom hint requests available for this puzzle"""
        if self.hunt.canned_hint_policy == Hunt.CannedHintPolicy.CANNED_ONLY:
            return 0
        elif self.hunt.canned_hint_policy == Hunt.CannedHintPolicy.CANNED_FIRST and puzzle_status.num_unused_canned_hints != 0:
            return 0
        if self.hunt.hint_pool_allocation == Hunt.HintPoolAllocation.HINT_TYPE_SPLIT:
            return self.num_available_hints
        elif self.hunt.hint_pool_type == Hunt.HintPoolType.GLOBAL_ONLY:
            return self.num_available_hints
        elif self.hunt.hint_pool_type == Hunt.HintPoolType.PUZZLE_ONLY:
            return puzzle_status.num_available_hints
        else:
            return self.num_available_hints + puzzle_status.num_available_hints
    
    def num_canned_hint_requests_available(self, puzzle_status):
        """Returns the number of canned hint requests available for this puzzle"""
        num_hints = 0
        if self.hunt.hint_pool_allocation == Hunt.HintPoolAllocation.HINT_TYPE_SPLIT:
            num_hints = puzzle_status.num_available_hints
        else:
            if self.hunt.hint_pool_type == Hunt.HintPoolType.GLOBAL_ONLY:
                num_hints = self.num_available_hints
            elif self.hunt.hint_pool_type == Hunt.HintPoolType.PUZZLE_ONLY:
                num_hints = puzzle_status.num_available_hints
            else:
                num_hints = self.num_available_hints + puzzle_status.num_available_hints

        if self.hunt.canned_hint_policy == Hunt.CannedHintPolicy.CANNED_ONLY:
            return min(num_hints, puzzle_status.num_unused_canned_hints)
        else:
            return num_hints
    

    def hint_uses_puzzle_pool(self, puzzle_status, is_canned_hint):
        """Returns whether the team's hints use the puzzle-specific pool"""
        match self.hunt.hint_pool_allocation:
            case Hunt.HintPoolAllocation.HINT_TYPE_SPLIT:
                return is_canned_hint
            case Hunt.HintPoolAllocation.PUZZLE_PRIORITY:
                return puzzle_status.num_available_hints > 0

    def process_unlocks(self, parsed_config=None):
        """
        Calculate what puzzles, points, hints, and badges this team has unlocked based on the hunt config.
        
        Returns:
            tuple: (set of unlocked puzzle IDs, total points, total hints)
        """
        hunt = self.hunt
        if self.playtester:
            start_time = self.playtest_start_date
            end_time = self.playtest_end_date
        else:
            start_time = hunt.start_date
            end_time = hunt.end_date
        
        if not self.hunt.config or timezone.now() < start_time or timezone.now() > end_time:
            return
        
        if parsed_config:
            config_rules = parsed_config
        else:
            puzzles = hunt.puzzle_set.values_list('id', 'order_number')
            puzzle_ids = set(p[0] for p in puzzles)
            order_to_id = {p[1]: p[0] for p in puzzles}
            try:
                # Parse the config and process unlocks
                config_rules = parse_config(self.hunt.config, puzzle_ids, order_to_id)
            except Exception as e:
                # Log the error if config parsing fails
                logger.error(f"Error processing hunt config: {e}")
                return
            
        puzzle_statuses = self.puzzlestatus_set.all()
        unlocked_puzzles, points, hints, puzzle_hints, earned_badges = process_config_rules(
            config_rules,
            puzzle_statuses,
            start_time,
            timezone.now()
        )
        
        # Unlock new puzzles
        current_unlocks = set(self.unlocked_puzzles().values_list('id', flat=True))
        puzzles_to_add = unlocked_puzzles - current_unlocks
        
        for puzzle_id in puzzles_to_add:
            new_status = PuzzleStatus.objects.create(
                team=self,
                puzzle_id=puzzle_id,
                unlock_time=timezone.now()
            )
        
        for puzzle_id, num_hints in puzzle_hints.items():
            try:
                status = PuzzleStatus.objects.get(team=self, puzzle_id=puzzle_id)
            except PuzzleStatus.DoesNotExist:
                continue
            if num_hints > status.num_total_hints_earned:
                PuzzleStatus.objects.filter(team=self, puzzle_id=puzzle_id).update(
                    num_available_hints=F('num_available_hints') + num_hints - F('num_total_hints_earned'),
                    num_total_hints_earned=num_hints
                )
    
        updated = False
        # Update points
        if points != self.points:
            Team.objects.filter(pk=self.pk).update(points=points)
            updated = True
        # Update hints
        if hints > self.num_total_hints_earned:
            updated = True
            Team.objects.filter(pk=self.pk).update(
                num_available_hints=F('num_available_hints') + hints - F('num_total_hints_earned'),
                num_total_hints_earned=hints
            )

        # Process badges (need to check current state)
        current_badges = self.badges
        new_badges = earned_badges
        if current_badges != new_badges:
            Team.objects.filter(pk=self.pk).update(badges=new_badges)
            updated = True

        if updated:
            self.refresh_from_db()

    def validate_members(self, adding_pks=None, removing_pks=None):
        """
        Validate member constraints
        adding_pks: set of user IDs being added
        removing_pks: set of user IDs being removed
        """
        if self.pk:  # Only check if team already exists
            # Calculate what the member count will be after the change
            current_count = self.members.count()
            if adding_pks:
                current_count += len(adding_pks)
            if removing_pks:
                current_count -= len(removing_pks)

            # Check team size limit
            if current_count > self.hunt.team_size_limit:
                raise ValidationError(
                    f'Team cannot have more than {self.hunt.team_size_limit} members'
                )
            
            # Check for members on multiple teams in same hunt
            if adding_pks:
                for user in User.objects.filter(id__in=adding_pks):
                    other_teams = user.team_set.filter(hunt=self.hunt).exclude(pk=self.pk)
                    if other_teams.exists():
                        raise ValidationError(
                            f'User {user.display_string()} is already on another team in this hunt'
                        )

    def natural_key(self):
        return (self.join_code,) + self.hunt.natural_key()

    def __str__(self):
        return f"{self.short_name} - {self.hunt.name}"

@receiver(m2m_changed, sender=Team.members.through)
def validate_team_members(sender, instance, action, pk_set, **kwargs):
    """Validate team members when the M2M relation changes"""
    if action == "pre_add":
        instance.validate_members(adding_pks=pk_set)
    elif action == "pre_remove":
        instance.validate_members(removing_pks=pk_set)

# endregion


class Submission(models.Model):
    """ A class representing a submission to a given puzzle from a given team """

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that made the submission")
    submission_time = models.DateTimeField()
    submission_text = models.CharField(
        max_length=100)
    response_text = models.CharField(
        blank=True,
        max_length=400,
        help_text="Response to the given answer.")
    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this submission is in response to")
    modified_time = models.DateTimeField(
        help_text="Last date/time of response modification")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The user who created the submission")
    matched_response = models.ForeignKey(
        'Response',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The custom Response that matched this submission (if any)")

    @property
    def is_correct(self):
        """ A boolean indicating if the submission given is exactly correct """
        if self.puzzle.case_sensitive:
            return self.submission_text == self.puzzle.answer
        else:
            return self.submission_text.lower() == self.puzzle.answer.lower()

    @property
    def convert_markdown_response(self):
        """ The response with all markdown links converted to HTML links """
        return re.sub(r'\[(.*?)]\((.*?)\)', '<a href="\\2">\\1</a>', self.response_text)

    def save(self, *args, **kwargs):
        """ Overrides the default save function to update the modified date on save """
        self.modified_time = timezone.now()
        is_new = not bool(self.pk)
        super(Submission, self).save(*args, **kwargs)
        # This is to ensure that the event is sent after the view has completed the transaction
        # It has no effect if the caller is not in a transaction
        puzzle_pk = self.puzzle.pk
        transaction.on_commit(lambda: send_event_to_team_members(self.team, f"submission-{puzzle_pk}", "modification"))
        if is_new:
            Event.objects.create_event(Event.EventType.PUZZLE_SUBMISSION, self, self.user)

    def respond(self):
        """ Takes the submission's text and uses various methods to craft and populate a response. """

        # Check against regexes
        matched_response = None
        for resp in self.puzzle.response_set.all():
            if re.match(resp.regex, self.submission_text, re.IGNORECASE):
                response = resp.text
                matched_response = resp
                break
        else:  # Give a default response if no regex matches
            if self.is_correct:
                response = "Correct"
            else:
                # Current philosophy is to auto-can wrong answers: If it's not right, it's wrong
                response = "Wrong Answer."

        self.response_text = response
        self.matched_response = matched_response

    def __str__(self):
        return f"{self.team_id}-{self.puzzle_id}-{self.submission_text}"


class PuzzleStatus(models.Model):
    """ A class representing the status of a puzzle for a team """
    class Meta:
        verbose_name_plural = "puzzle statuses"
        unique_together = ('puzzle', 'team',)

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle this status is for")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that this puzzle status for")
    unlock_time = models.DateTimeField(
        help_text="The time this puzzle was unlocked for this team")
    solve_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The time this puzzle was solved for this team")
    num_available_hints = models.IntegerField(
        default=0,
        help_text="Number of puzzle-specific hints available"
    )
    num_total_hints_earned = models.IntegerField(
        default=0,
        help_text="The total number of puzzle-specific hints this puzzle/team pair has earned"
    )

    def __str__(self):
        return f"{self.team.short_name} => {self.puzzle.name}"
    
    def save(self, *args, **kwargs):
        is_new = not bool(self.pk)
        super().save(*args, **kwargs)
        if is_new:
            # This is to ensure that the event is sent after the view has completed the transaction
            # It has no effect if the caller is not in a transaction
            transaction.on_commit(lambda: send_event_to_team_members(self.team, "huntUpdate", "unlock"))
            Event.objects.create_event(Event.EventType.PUZZLE_UNLOCK, self, user=None)

    def mark_solved(self):
        """ Update the solved timestamp to indicate this puzzle has been solved. """
        # Make sure we don't update the solve time if it is already solved
        if self.solve_time is not None:
            return
        self.solve_time = timezone.now()
        self.save()
        self.team.process_unlocks()
        # This is to ensure that the event is sent after the view has completed the transaction
        # It has no effect if the caller is not in a transaction
        transaction.on_commit(lambda: send_event_to_team_members(self.team, "huntUpdate", "solve"))
        Event.objects.create_event(Event.EventType.PUZZLE_SOLVE, self, user=None)
        if self.puzzle.type == Puzzle.PuzzleType.FINAL_PUZZLE:
            Event.objects.create_event(Event.EventType.FINISH_HUNT, self, user=None)

    @cached_property
    def next_canned_hint(self):
        """Returns the next available canned hint or None if all used"""
        return self.puzzle.cannedhint_set.order_by('order')[self.num_canned_hints_used:self.num_canned_hints_used + 1].first()

    @cached_property
    def num_canned_hints_used(self):
        """Returns the number of canned hints that have been revealed to this team"""
        return Hint.objects.filter(team=self.team, puzzle=self.puzzle, canned_hint__isnull=False).count()

    @cached_property
    def num_unused_canned_hints(self):
        """Returns the number of unused canned hints"""
        return self.puzzle.cannedhint_set.count() - self.num_canned_hints_used

    @property
    def num_custom_hint_requests_available(self):
        """Returns the number of custom hint requests available for this puzzle"""
        return self.team.num_custom_hint_requests_available(self)
    
    @property
    def num_canned_hint_requests_available(self):
        """Returns the number of canned hint requests available for this puzzle"""
        return self.team.num_canned_hint_requests_available(self)
    
    def hint_uses_puzzle_pool(self, is_canned_hint):
        return self.team.hint_uses_puzzle_pool(self, is_canned_hint)


class ResponseManager(models.Manager):
    def get_by_natural_key(self, puzzle_id, regex):
        return self.get(puzzle_id=puzzle_id, regex=regex)

class Response(models.Model):
    """ A class to represent an automated response regex """
    class Meta:
        verbose_name_plural = "Auto Responses"
        unique_together = [('puzzle', 'regex')]

    objects = ResponseManager()

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this automated response is related to")
    regex = models.CharField(
        max_length=400,
        help_text="The python-style regex that will be checked against the user's response")
    text = models.CharField(
        max_length=400,
        help_text="The text to use in the submission response if the regex matched")

    def __str__(self):
        return f"{self.puzzle}: {self.regex} -> {self.text}"

    def natural_key(self):
        return (self.puzzle_id, self.regex)


class Hint(models.Model):
    """ A class to represent a hint to a puzzle """

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle that this hint is related to")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        help_text="The team that requested the hint")
    request = models.TextField(
        max_length=1000,
        help_text="The text of the request for the hint")
    request_time = models.DateTimeField(
        help_text="Hint request time")
    response = models.TextField(
        max_length=1000,
        blank=True,
        help_text="The text of the response to the hint request")
    response_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Hint response time")
    last_modified_time = models.DateTimeField(
        help_text="Last time of modification")
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="Staff member that has claimed the hint.")
    refunded = models.BooleanField(
        help_text="Whether or not the hint was refunded",
        default=False,
    )
    from_puzzle_pool = models.BooleanField(
        default=False,
        help_text="Whether this hint was drawn from the puzzle-specific pool"
    )
    canned_hint = models.ForeignKey(
        'CannedHint',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="If this was a canned hint, which one"
    )

    def send_hint_sse(self, data, send_team_msg=False):
        """Send SSE update to staff hints page and optionally team hints UI."""
        send_event("staff", "hints", data)
        if send_team_msg:
            send_event_to_team_members(self.team, "hints", data)

    def save(self, *args, **kwargs):
        """Override save to decrement the correct hint pool"""
        is_new = not bool(self.pk)
        if is_new:  # Only trigger this section on creation
            team = self.team
            try:
                status = PuzzleStatus.objects.get(team=team, puzzle=self.puzzle)
            except PuzzleStatus.DoesNotExist:
                raise ValidationError("Puzzle status does not exist")
            is_canned_hint = self.canned_hint is not None
            if status.hint_uses_puzzle_pool(is_canned_hint):
                status.num_available_hints = F("num_available_hints") - 1
                status.save(update_fields=["num_available_hints"])
                self.from_puzzle_pool = True
            else:
                team.num_available_hints = F("num_available_hints") - 1
                team.save(update_fields=["num_available_hints"])
                self.from_puzzle_pool = False
            self.send_hint_sse("request", True)
        super().save(*args, **kwargs)
        if is_new:
            Event.objects.create_event(Event.EventType.HINT_REQUEST, self, user=None)

    @property
    def answered(self):
        """ A boolean indicating if the hint has been answered """
        return self.response != ""

    @property
    def status(self):
        """ A string indicating the status of the hint """
        if self.answered:
            return "answered"
        elif self.responder:
            return "claimed"
        else:
            return "unclaimed"

    def claim(self, user):
        self.responder = user
        self.save()
        self.send_hint_sse("claim")
        return self

    def release(self):
        self.responder = None
        self.save()
        self.send_hint_sse("release")
        return self

    def respond(self, user, response):
        notification_type = "response" if self.response == "" else "response_update"
        self.response = response
        self.response_time = timezone.now()
        self.responder = user
        self.last_modified_time = timezone.now()
        self.save()
        self.send_hint_sse(notification_type, True)
        Event.objects.create_event(
            Event.EventType.HINT_RESPONSE,
            self,
            user,
            related_data=notification_type
        )
        return self

    def refund(self):
        """Refund a hint to the correct pool"""
        if self.refunded:
            return self
        self.refunded = True
        self.last_modified_time = timezone.now()
        self.save()
        team = self.team
        if self.from_puzzle_pool:
            status = PuzzleStatus.objects.get(team=team, puzzle=self.puzzle)
            status.num_available_hints = F("num_available_hints") + 1
            status.save(update_fields=["num_available_hints"])
        else:
            team.num_available_hints = F("num_available_hints") + 1
            team.save(update_fields=["num_available_hints"])
        self.send_hint_sse("refund", True)
        Event.objects.create_event(Event.EventType.HINT_REFUND, self, user=None)
        return self

    def __str__(self):
        return self.team.short_name + ": " + self.puzzle.name + " (" + str(self.request_time) + ")"


class CannedHintManager(models.Manager):
    def get_by_natural_key(self, puzzle_id, order):
        return self.get(puzzle__id=puzzle_id, order=order)

class CannedHint(models.Model):
    """A pre-written hint that can be revealed to teams"""

    objects = CannedHintManager()

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        help_text="The puzzle this canned hint belongs to"
    )
    text = models.TextField(
        max_length=1000,
        help_text="The text of the hint"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order in which this hint should be shown (lower numbers first)"
    )
    
    class Meta:
        ordering = ['order']
        unique_together = ['puzzle', 'order']

    def __str__(self):
        return f"{self.puzzle.name} - Hint #{self.order}"

    def natural_key(self):
        return (self.puzzle.id, self.order)


class TeamRankingRuleManager(models.Manager):
    def get_by_natural_key(self, hunt_name, hunt_start_date, rule_order):
        hunt = Hunt.objects.get_by_natural_key(hunt_name, hunt_start_date)
        return self.get(hunt=hunt, rule_order=rule_order)

class TeamRankingRule(models.Model):
    """ A class to represent the rules used to rank teams """
    class RuleType(models.TextChoices):
        NUM_UNLOCKS = 'UNLK', 'Number of Puzzles Unlocked'
        NUM_PUZZLES = 'PUZZ', 'Number of Puzzles Solved'
        NUM_METAS = 'META', 'Number of Metas Solved'
        FINAL_SOLVE_TIME = 'FINL', 'Final Puzzle Solve Time'
        LAST_META_TIME = 'LMTM', 'Last Meta Solve Time'
        LAST_SOLVE_TIME = 'LAST', 'Last Solve Time'
        NUM_POINTS = 'PNTS', 'Number of Points'
        NUM_HINTS_LEFT = 'HINT', 'Number of Hints Left'

    class Meta:
        unique_together = ('hunt', 'rule_order')

    objects = TeamRankingRuleManager()

    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that this ranking rule refers to")

    rule_type = models.CharField(
        max_length=4,
        choices=RuleType.choices,
        help_text="The type of ranking rule"
    )

    rule_order = models.IntegerField(
        help_text="The order in which the rule is applied")

    visible = models.BooleanField(
        default=True,
        help_text="Is this rule visible on the leaderboard?"
    )

    @property
    def is_time(self):
        return (self.rule_type == self.RuleType.FINAL_SOLVE_TIME or
                self.rule_type == self.RuleType.LAST_META_TIME or
                self.rule_type == self.RuleType.LAST_SOLVE_TIME)

    @property
    def display_name(self):
        match self.rule_type:
            case self.RuleType.NUM_UNLOCKS:
                return "# Unlocks"
            case self.RuleType.NUM_PUZZLES:
                return "# Solves"
            case self.RuleType.NUM_METAS:
                return "# Meta Solves"
            case self.RuleType.FINAL_SOLVE_TIME:
                return "Finish Time"
            case self.RuleType.LAST_META_TIME:
                return "Last Meta Solve Time"
            case self.RuleType.LAST_SOLVE_TIME:
                return "Last Solve Time"
            case self.RuleType.NUM_POINTS:
                return "# Points"
            case self.RuleType.NUM_HINTS_LEFT:
                return "# Hints left"

    @property
    def ordering_parameter(self):
        match self.rule_type:
            case (self.RuleType.NUM_PUZZLES | self.RuleType.NUM_METAS | self.RuleType.NUM_POINTS |
                  self.RuleType.NUM_HINTS_LEFT | self.RuleType.NUM_UNLOCKS):
                return F(self.rule_type).desc(nulls_last=True)
            case self.RuleType.FINAL_SOLVE_TIME | self.RuleType.LAST_META_TIME | self.RuleType.LAST_SOLVE_TIME:
                return F(self.rule_type).asc(nulls_last=True)

    def annotate_query(self, query):
        match self.rule_type:
            case self.RuleType.NUM_UNLOCKS:
                sq = PuzzleStatus.objects.filter(team__pk=OuterRef('pk'),  unlock_time__isnull=False).order_by()
                sq = sq.values('team').annotate(c=Count('*')).values('c')
                args = {self.rule_type: Subquery(sq, output_field=PositiveIntegerField())}
                return query.annotate(**args)
            case self.RuleType.NUM_PUZZLES:
                sq = PuzzleStatus.objects.filter(team__pk=OuterRef('pk'), solve_time__isnull=False).order_by()
                sq = sq.values('team').annotate(c=Count('*')).values('c')
                args = {self.rule_type: Subquery(sq, output_field=PositiveIntegerField())}
                return query.annotate(**args)
            case self.RuleType.NUM_METAS:
                sq = PuzzleStatus.objects.filter(Q(puzzle__type=Puzzle.PuzzleType.META_PUZZLE) | Q(puzzle__type=Puzzle.PuzzleType.FINAL_PUZZLE))
                sq = sq.filter(team__pk=OuterRef('pk'), solve_time__isnull=False).order_by()
                sq = sq.values('team').annotate(c=Count('*')).values('c')
                args = {self.rule_type: Subquery(sq, output_field=PositiveIntegerField())}
                return query.annotate(**args)
            case self.RuleType.FINAL_SOLVE_TIME:
                sq = PuzzleStatus.objects.filter(team__pk=OuterRef('pk'), puzzle__type=Puzzle.PuzzleType.FINAL_PUZZLE,
                                                 solve_time__isnull=False).order_by()
                sq = sq.values('team').annotate(last_time=Max('solve_time')).values('last_time')
                args = {self.rule_type: Subquery(sq, output_field=DateTimeField())}
                return query.annotate(**args)
            case self.RuleType.LAST_META_TIME:
                sq = PuzzleStatus.objects.filter(Q(puzzle__type=Puzzle.PuzzleType.META_PUZZLE) | Q(puzzle__type=Puzzle.PuzzleType.FINAL_PUZZLE))
                sq = sq.filter(team__pk=OuterRef('pk'), solve_time__isnull=False).order_by()
                sq = sq.values('team').annotate(last_time=Max('solve_time')).values('last_time')
                args = {self.rule_type: Subquery(sq, output_field=DateTimeField())}
                return query.annotate(**args)
            case self.RuleType.LAST_SOLVE_TIME:
                sq = PuzzleStatus.objects.filter(team__pk=OuterRef('pk'), solve_time__isnull=False).order_by()
                sq = sq.values('team').annotate(last_time=Max('solve_time')).values('last_time')
                args = {self.rule_type: Subquery(sq, output_field=DateTimeField())}
                return query.annotate(**args)
            case self.RuleType.NUM_POINTS:
                return query.annotate(**{self.rule_type: F("points")})
            case self.RuleType.NUM_HINTS_LEFT:
                return query.annotate(**{self.rule_type: F("num_available_hints")})

    def natural_key(self):
        return self.hunt.natural_key() + (self.rule_order,)


class Update(models.Model):
    """ A class to represent puzzle/hunt updates """
    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt that update is part of")

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="The puzzle this update relates to (leave blank for hunt updates)")

    text = models.TextField(
        max_length=1000,
        help_text="The text of the update announcement.")

    time = models.DateTimeField(
        help_text="The time the update was announced")
    
    def save(self, *args, **kwargs):
        is_new = not bool(self.pk)
        super().save(*args, **kwargs)
        if is_new:
            Event.objects.create_event(Event.EventType.UPDATE, self, user=None)


class EventManager(models.Manager):
    def create_event(self, event_type, related_object, user, related_data=None):
        timestamp = timezone.now()
        extra_data = related_data if related_data else dict()
        team = None
        puzzle = None
        hunt = None
        match event_type:
            case Event.EventType.PUZZLE_SUBMISSION:  # related object submission
                timestamp = related_object.submission_time
                puzzle = related_object.puzzle
                team = related_object.team
                extra_data = related_object.submission_text
                hunt = team.hunt
            case Event.EventType.PUZZLE_SOLVE:  # related object puzzleStatus
                timestamp = related_object.solve_time
                puzzle = related_object.puzzle
                team = related_object.team
                hunt = team.hunt
            case Event.EventType.PUZZLE_UNLOCK:  # related object puzzleStatus
                timestamp = related_object.unlock_time
                puzzle = related_object.puzzle
                team = related_object.team
                hunt = team.hunt
            case Event.EventType.HINT_REQUEST:  # related object hint
                timestamp = related_object.request_time
                puzzle = related_object.puzzle
                team = related_object.team
                extra_data = "canned" if related_object.canned_hint is not None else "custom"
                hunt = team.hunt
            case Event.EventType.HINT_RESPONSE:  # related object hint
                timestamp = related_object.response_time
                puzzle = related_object.puzzle
                team = related_object.team
                # related_data can be "response" or "response_update"
                if not related_data:
                    extra_data = "response"
                hunt = team.hunt
            case Event.EventType.HINT_REFUND:  # related object hint
                timestamp = related_object.last_modified_time
                puzzle = related_object.puzzle
                team = related_object.team
                hunt = team.hunt
            case Event.EventType.FINISH_HUNT:  # related object puzzleStatus (for final puzzle)
                timestamp = related_object.solve_time
                team = related_object.team
                hunt = team.hunt
            case Event.EventType.TEAM_JOIN:  # related object team
                team = related_object
                hunt = team.hunt
            case Event.EventType.UPDATE:  # related object update
                timestamp = related_object.time
                if related_object.puzzle is not None:
                    puzzle = related_object.puzzle
                hunt = related_object.hunt

        related_object_id = ""
        if isinstance(related_object, models.Model):
            related_object_id = related_object.id

        # Send all events to the staff channel for the feed page
        event_metadata = {
            "type": event_type,
            "team_id": team.pk if team else None,
            "puzzle_id": puzzle.pk if puzzle else None,
        }
        send_event("staff", "events", event_metadata)

        event = self.create(
            timestamp=timestamp,
            type=event_type,
            related_data=extra_data if len(extra_data) > 0 else '',
            related_object_id=related_object_id,
            user=user,
            hunt=hunt,
            team=team,
            puzzle=puzzle,
        )

        from .notifications import send_event_notifications
        transaction.on_commit(lambda: send_event_notifications(event.pk))

        return event


class Event(models.Model):
    class EventType(models.TextChoices):
        # Common Types
        PUZZLE_SUBMISSION = 'PSUB', 'Submission'
        PUZZLE_SOLVE = 'PSOL', 'Solve'
        PUZZLE_UNLOCK = 'PUNL', 'Unlock'
        HINT_REQUEST = 'HREQ', 'Hint Request'
        HINT_RESPONSE = 'HRES', 'Hint Response'
        HINT_REFUND = 'HREF', 'Hint Refund'
        FINISH_HUNT = 'FINH', 'Finish Hunt'

        # Queue-only Types
        TEAM_JOIN = 'TMJH', 'Team Join'

        # Public-only Types
        UPDATE = 'UPDT', 'New Update'

    queue_types = [EventType.PUZZLE_SUBMISSION, EventType.PUZZLE_SOLVE, EventType.PUZZLE_UNLOCK,
                   EventType.HINT_REQUEST, EventType.HINT_RESPONSE, EventType.HINT_REFUND,
                   EventType.FINISH_HUNT, EventType.TEAM_JOIN]
    public_types = [EventType.PUZZLE_SUBMISSION, EventType.PUZZLE_SOLVE, EventType.PUZZLE_UNLOCK,
                    EventType.HINT_REQUEST, EventType.HINT_RESPONSE, EventType.HINT_REFUND,
                    EventType.FINISH_HUNT, EventType.UPDATE]

    # Every event has a user, a team, and a hunt, some have a puzzle
    # (Except update which doesn't have a team)
    timestamp = models.DateTimeField(
        help_text="The time of the event")
    type = models.CharField(
        max_length=4,
        choices=EventType.choices,
        help_text="The type of event")
    related_data = models.CharField(
        max_length=400,
        blank=True)
    related_object_id = models.CharField(
        max_length=30,
        blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        help_text="The user associated with this event")
    hunt = models.ForeignKey(
        Hunt,
        on_delete=models.CASCADE,
        help_text="The hunt associated with this event")
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="The team associated with this event, if applicable")
    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="The puzzle associated with this event, if applicable")

    objects = EventManager()

    @cached_property
    def related_object(self):
        match self.type:
            case Event.EventType.PUZZLE_SUBMISSION:
                return Submission.objects.get(pk=self.related_object_id)
            case Event.EventType.PUZZLE_SOLVE:
                return PuzzleStatus.objects.get(pk=self.related_object_id)
            case Event.EventType.PUZZLE_UNLOCK:
                return PuzzleStatus.objects.get(pk=self.related_object_id)
            case Event.EventType.HINT_REQUEST:
                return Hint.objects.get(pk=self.related_object_id)
            case Event.EventType.HINT_RESPONSE:
                return Hint.objects.get(pk=self.related_object_id)
            case Event.EventType.HINT_REFUND:
                return Hint.objects.get(pk=self.related_object_id)
            case Event.EventType.FINISH_HUNT:
                return PuzzleStatus.objects.get(pk=self.related_object_id)
            case Event.EventType.TEAM_JOIN:
                return Team.objects.get(pk=self.related_object_id)
            case Event.EventType.UPDATE:
                return Update.objects.get(pk=self.related_object_id)
            case _:
                return None

    @property
    def color(self):
        match self.type:
            case Event.EventType.PUZZLE_SUBMISSION:
                if self.related_object.is_correct:
                    return "#a3d7a3"
                else:
                    return "#ff9999"
            case Event.EventType.PUZZLE_SOLVE:
                return "#079103"
            case Event.EventType.PUZZLE_UNLOCK:
                return "#a3c7ff"
            case Event.EventType.HINT_REQUEST:
                return "#f5b78a"
            case Event.EventType.HINT_RESPONSE:
                return "#dcdc9f"
            case Event.EventType.HINT_REFUND:
                return "#b8e6b8"
            case Event.EventType.FINISH_HUNT:
                return "#d6a3ff"
            case Event.EventType.TEAM_JOIN:
                return "#aaaaaa"
            case _:
                return "#cccccc"

    @property
    def icon(self):
        match self.type:
            case Event.EventType.PUZZLE_SUBMISSION:
                if self.related_object.is_correct:
                    return "fa-check"
                else:
                    return "fa-ban"
            case Event.EventType.PUZZLE_SOLVE:
                return "fa-puzzle-piece"
            case Event.EventType.PUZZLE_UNLOCK:
                return "fa-unlock"
            case Event.EventType.HINT_REQUEST:
                return "fa-question"
            case Event.EventType.HINT_RESPONSE:
                return "fa-reply"
            case Event.EventType.HINT_REFUND:
                return "fa-undo"
            case Event.EventType.FINISH_HUNT:
                return "fa-flag-checkered"
            case Event.EventType.TEAM_JOIN:
                return "fa-plus"
            case _:
                return ""

    @property
    def web_text(self):
        match self.type:
            case Event.EventType.PUZZLE_SUBMISSION:
                return f"<b>{ self.team.name }</b> submitted <b>{ self.related_data }</b> to <b>{ self.puzzle.name }</b>."
            case Event.EventType.PUZZLE_SOLVE:
                return f"<b>{ self.team.name }</b> has solved <b>{ self.puzzle.name }</b>!"
            case Event.EventType.PUZZLE_UNLOCK:
                return f"<b>{ self.team.name }</b> has unlocked <b>{ self.puzzle.name }</b>."
            case Event.EventType.HINT_REQUEST:
                return f"<b>{ self.team.name }</b> has requested a { self.related_data if self.related_data != '{}' else ''} hint for <b>{ self.puzzle.name }</b>."
            case Event.EventType.HINT_RESPONSE:
                return (f"<b>{ self.user.first_name } { self.user.last_name }</b> has responded to the hint request from "
                        f"<b>{ self.team.name }</b> for <b>{ self.puzzle.name }</b>.")
            case Event.EventType.HINT_REFUND:
                return f"A hint has been refunded for <b>{ self.team.name }</b> on <b>{ self.puzzle.name }</b>."
            case Event.EventType.FINISH_HUNT:
                return f"Team <b>{ self.team.name }</b> has finished!"
            case Event.EventType.TEAM_JOIN:
                return f"Team <b>{ self.team.name }</b> has joined!"
            case _:
                return ""
    @property
    def notification_text(self):
        match self.type:
            case Event.EventType.PUZZLE_SUBMISSION:
                return f"{ self.user.display_string() } has submitted { self.related_data } to { self.puzzle.name }."
            case Event.EventType.PUZZLE_SOLVE:
                return f"Your team has solved { self.puzzle.name }!"
            case Event.EventType.PUZZLE_UNLOCK:
                return f"Your team has unlocked { self.puzzle.name }."
            case Event.EventType.HINT_REQUEST:
                return f"Your team has requested a hint for { self.puzzle.name }."
            case Event.EventType.HINT_RESPONSE:
                if self.related_data == "response_update":
                    return f"Your hint response has been updated for { self.puzzle.name }."
                return f"Staff has responded to your hint request for { self.puzzle.name }."
            case Event.EventType.HINT_REFUND:
                return f"Your hint has been refunded for { self.puzzle.name }."
            case Event.EventType.FINISH_HUNT:
                return f"Your team has finished!"
            case Event.EventType.UPDATE:
                return f"New update for { self.hunt.name }: { self.related_data }"
            case _:
                return ""


class DisplayOnlyHunt(models.Model):
    """ Model for the display only hunt, only to be shown on the archive page """

    name = models.CharField(
        max_length=200,
        help_text="The name of the hunt as the public will see it")
    display_start_date = models.DateTimeField(
        help_text="The date/time at which a hunt will become visible to registered users")
    display_end_date = models.DateTimeField(
        help_text="The date/time at which a hunt will be archived and available to the public")
    num_teams = models.IntegerField(
        help_text="The number of teams that were registered for this hunt")
    num_puzzles = models.IntegerField(
        help_text="The number of puzzles this hunt had")

    def __str__(self):
        return self.name


class NotificationPlatform(models.Model):
    """A platform that can be used to send notifications (Browser, Email, Webhook)"""

    class PlatformType(models.TextChoices):
        BROWSER = 'BRWS', 'Browser'
        EMAIL = 'MAIL', 'Email'
        WEBHOOK = 'WHBK', 'Webhook'

    type = models.CharField(
        max_length=4,
        choices=PlatformType.choices,
        help_text="The type of notification platform")
    name = models.CharField(
        max_length=100,
        help_text="A friendly name for this platform configuration")
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this platform is currently enabled")
    config = models.JSONField(
        null=True,
        blank=True,
        help_text="Platform-specific configuration (API keys, URLs, etc.)")

    def __str__(self):
        return self.name

    def clean(self):
        """Validate platform configuration using handler's validate_config method"""
        from .notifications import NotificationHandler
        handler_class = NotificationHandler.get_handler(self.type)
        if handler_class:
            try:
                handler_class.validate_config(self.config or {})
            except ValidationError as e:
                raise ValidationError({'config': e.message if hasattr(e, 'message') else str(e)})

    class Meta:
        unique_together = ['type', 'name']


class NotificationSubscription(models.Model):
    """A user's subscription to notifications for specific event types"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="The user who owns this subscription")
    platform = models.ForeignKey(
        NotificationPlatform,
        on_delete=models.CASCADE,
        help_text="The platform to send notifications through")
    hunt = models.ForeignKey(
        'Hunt',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Optional: limit notifications to a specific hunt")
    event_types = models.CharField(
        max_length=255,
        help_text="Comma-separated list of event types to notify on")
    destination = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        help_text="Platform-specific destination (webhook URL, email, channel ID, etc.)")
    active = models.BooleanField(
        default=True,
        help_text="Whether this subscription is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        hunt_str = f" ({self.hunt.name})" if self.hunt else " (All Hunts)"
        return f"{self.user.display_string()} - {self.platform.name}{hunt_str}"

    @property
    def event_types_list(self):
        """Returns the event types as a list"""
        return [t.strip() for t in self.event_types.split(',') if t.strip()]

    def clean(self):
        """Validate event_types and destination"""
        # Validate event types
        invalid_types = set(self.event_types_list) - set(Event.EventType.values)
        if invalid_types:
            raise ValidationError({
                'event_types': f"Invalid event types: {', '.join(invalid_types)}"
            })

        # Validate destination using the platform's handler
        from .notifications import NotificationHandler
        handler = NotificationHandler.create_handler(self.platform)
        if handler:
            try:
                handler.validate_destination(self.destination)
            except ValidationError as e:
                raise ValidationError({'destination': e.message})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
