from django.contrib import admin
from django.db.models.functions import Lower

from puzzlehunt.models import Hunt, Puzzle, Prepuzzle, Team, PuzzleStatus, Submission, User, Event,\
    Response, Hint, Update, TeamRankingRule, PuzzleFile, SolutionFile, HuntFile,\
    PrepuzzleFile, DisplayOnlyHunt, NotificationPlatform, NotificationSubscription, CannedHint
from puzzlehunt.utils import create_media_files
from admin_interface.models import Theme
from django.utils.translation import gettext_lazy as _

from django import forms
from django.contrib.auth.models import Group
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.admin import Site
from django.template.defaultfilters import truncatechars
from django.utils.safestring import mark_safe
from puzzlehunt.widgets import AceEditorWidget


admin.site.unregister(Group)
admin.site.unregister(FlatPage)
admin.site.unregister(Theme)


@admin.display(description="Team name", ordering=Lower("team__name"))
def short_team_name(teamable_object):
    try:
        return truncatechars(teamable_object.team.name, 50)
    except:
        return truncatechars(teamable_object.name, 50)


@admin.register(User)
class PuzzlehuntUserAdmin(admin.ModelAdmin):
    search_fields = ['email', 'display_name', 'first_name', 'last_name']
    list_display = ['email', 'display_name', 'is_staff', 'full_name']
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "display_name")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    # This sets details about the create user page because django is weird.
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("display_name", "password1", "password2")}),
    )


class TeamRankingRuleInline(admin.TabularInline):
    model = TeamRankingRule
    extra = 1
    ordering = ('rule_order',)
    fields = ['rule_order', 'rule_type', 'visible']


class HuntAdminForm(forms.ModelForm):
    model = Hunt

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(self.fields) != 0:
            if self.instance.pk:
                self.fields["css_file"].queryset = self.instance.files.all()
            else:
                self.fields["css_file"].queryset = HuntFile.objects.none()


@admin.register(Hunt)
class HuntAdmin(admin.ModelAdmin):
    form = HuntAdminForm
    inlines = (TeamRankingRuleInline,)
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'is_current_hunt', 'team_size_limit', 'location',
                        ('start_date', 'display_start_date'), ('end_date', 'display_end_date'))}),
        ('Hunt Behaviour', {'fields': ('hint_lockout', 'hint_pool_type', 'canned_hint_policy', 'hint_pool_allocation')}),
        ('Template', {'fields': ('template_file', 'css_file', 'info_page_file')}),
    )

    list_display = ['name', 'team_size_limit', 'start_date', 'is_current_hunt']


class PuzzleAdminForm(forms.ModelForm):
    model = Puzzle

    puzzle_source_file = forms.FileField(required=False)
    solution_source_file = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["main_file"].queryset = self.instance.files.all()
            self.fields["main_solution_file"].queryset = self.instance.solution_files.all()

    def clean(self):
        data = self.cleaned_data
        allow_spaces = data.get('allow_spaces')
        allow_non_alphanumeric = data.get('allow_non_alphanumeric')
        answer = data.get('answer')

        if answer:
            if not allow_spaces and ' ' in answer:
                raise forms.ValidationError("The answer contains spaces, but 'allow_spaces' is not checked.")
            # Checks for case sensitivity are done in the Submission.is_correct method
            if not allow_non_alphanumeric and not answer.isalnum():
                raise forms.ValidationError("The answer contains non-alphanumeric characters, but 'allow_non_alphanumeric' is not checked.")

        return data


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 1


@admin.register(Puzzle)
class PuzzleAdmin(admin.ModelAdmin):
    form = PuzzleAdminForm

    list_filter = ('hunt',)
    search_fields = ['id', 'name']
    list_display = ['id',  'name', 'hunt', 'type']
    list_display_links = ['id', 'name']
    ordering = ['-hunt', 'order_number']
    inlines = (ResponseInline,)
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'hunt', 'name', 'type', 'order_number')
        }),
        ('Answer Settings', {
            'fields': ('answer', 'allow_spaces', 'case_sensitive', 'allow_non_alphanumeric')
        }),
        ('Puzzle Files', {
            'fields': ('main_file', 'puzzle_source_file', 'main_solution_file', 'solution_source_file')
        }),
        ('Additional Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        file = form.cleaned_data.get('puzzle_source_file')
        if file is not None:
            create_media_files(obj, file)
        file = form.cleaned_data.get('solution_source_file')
        if file is not None:
            create_media_files(obj, file, is_solution_file=True)

        super().save_model(request, obj, form, change)


class PrepuzzleAdminForm(forms.ModelForm):
    model = Prepuzzle

    prepuzzle_source_file = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["main_file"].queryset = self.instance.files.all()

    def clean(self):
        data = self.cleaned_data
        allow_spaces = data.get('allow_spaces')
        allow_non_alphanumeric = data.get('allow_non_alphanumeric')
        answer = data.get('answer')

        if answer:
            if not allow_spaces and ' ' in answer:
                raise forms.ValidationError("The answer contains spaces, but 'allow_spaces' is not checked.")
            # Checks for case sensitivity are done in the Submission.is_correct method
            if not allow_non_alphanumeric and not answer.isalnum():
                raise forms.ValidationError("The answer contains non-alphanumeric characters, but 'allow_non_alphanumeric' is not checked.")

        return data


@admin.register(Prepuzzle)
class PrepuzzleAdmin(admin.ModelAdmin):
    form = PrepuzzleAdminForm
    list_display = ['name', 'hunt', 'released']
    readonly_fields = ('puzzle_url',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'released', 'hunt', 'puzzle_url')
        }),
        ('Answer Settings', {
            'fields': ('answer', 'allow_spaces', 'case_sensitive', 'allow_non_alphanumeric', 'response_string')
        }),
        ('Puzzle Files', {
            'fields': ('main_file', 'prepuzzle_source_file')
        }),
    )

    # Needed to add request to modelAdmin
    def get_queryset(self, request):
        qs = super(PrepuzzleAdmin, self).get_queryset(request)
        self.request = request
        return qs

    def puzzle_url(self, obj):
        puzzle_url_str = "http://" + self.request.get_host() + "/prepuzzle/" + str(obj.pk) + "/"
        html = "<script> function myFunction() { "
        html += "var copyText = document.getElementById('puzzleURL'); "
        html += "copyText.select(); "
        html += "document.execCommand('copy'); } </script>"
        html += "<input readonly style='width: 400px;' type=\"text\""
        html += "value=\"" + puzzle_url_str + "\" id=\"puzzleURL\">"
        html += "<button onclick=\"myFunction()\" type=\"button\">Copy Puzzle URL</button>"
        return mark_safe(html)

    def save_model(self, request, obj, form, change):
        file = form.cleaned_data.get('prepuzzle_source_file')
        if file is not None:
            create_media_files(obj, file)
        super().save_model(request, obj, form, change)

    puzzle_url.short_description = 'Puzzle URL: (Not editable)'


class PuzzleStatusInline(admin.StackedInline):
    model = PuzzleStatus
    fields = ('puzzle', ('unlock_time', 'solve_time'))
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = [short_team_name, 'hunt', 'is_local', 'playtester']
    list_filter = ['hunt']
    filter_horizontal = ['members']
    fieldsets = (
        # TODO: make this warning more field specific
        ("!!! Don't edit teams during a hunt unless absolutely necessary. Race conditions may occur. !!!",
         {
            'fields': ['name', 'hunt', 'members', 'is_local', 'join_code', 'num_available_hints'],
         }),
        ("Playtesting",
         {
             'fields': ['playtester', 'playtest_start_date', 'playtest_end_date',]
         })
    )

    # TODO: find a way to slim down this inline in order to bring it back.
    # inlines = [PuzzleStatusInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    search_fields = ['submission_text']
    list_filter = ['puzzle', 'submission_time']
    list_display = ['submission_text', short_team_name, 'submission_time']
    autocomplete_fields = ['team', 'user']


@admin.register(PuzzleStatus)
class PuzzleStatusAdmin(admin.ModelAdmin):
    list_display = [short_team_name, 'puzzle', 'solved']
    autocomplete_fields = ['team']

    @admin.display(boolean=True, description="Solved?")
    def solved(self, puzzle_status):
        return puzzle_status.solve_time is not None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "team":
            kwargs["queryset"] = Team.objects.select_related("hunt")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Hint)
class HintAdmin(admin.ModelAdmin):
    list_filter = ('puzzle__hunt', 'puzzle')
    list_display = [short_team_name, 'puzzle', 'request_time', 'has_been_answered']
    autocomplete_fields = ['responder', 'team']

    @admin.display(boolean=True, description="Answered?")
    def has_been_answered(self, hint):
        return hint.answered


@admin.register(Update)
class UpdateAdmin(admin.ModelAdmin):
    list_filter = ('hunt',)
    list_display = ['hunt', 'puzzle', 'time']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # search_fields = ['submission_text']
    list_filter = ['hunt', 'type']
    list_display = ['timestamp', 'type', 'user']
    autocomplete_fields = ['team', 'user']


class FlatPageProxyObject(FlatPage):
    class Meta:
        proxy = True
        app_label = 'puzzlehunt'
        verbose_name = "info page"
        verbose_name_plural = "info pages"


class FlatpageProxyForm(FlatpageForm):
    class Meta:
        model = FlatPageProxyObject
        fields = '__all__'


# Define a new FlatPageAdmin
@admin.register(FlatPageProxyObject)
class FlatPageProxyAdmin(FlatPageAdmin):
    list_filter = []
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content')}),
        (None, {
            'classes': ('hidden',),
            'fields': ('sites',)
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': (
                'registration_required',
                'template_name',
            ),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super(FlatPageAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['sites'].initial = Site.objects.get(pk=1)
        form.base_fields['content'].widget = AceEditorWidget(attrs={
            'style': 'width:90%;',
        })
        form.base_fields['url'].help_text = ("Example: '/contact-us/' translates to " +
                                         "/info/contact-us/. Make sure to have leading and " +
                                         "trailing slashes.")
        return form


@admin.register(DisplayOnlyHunt)
class DisplayOnlyHuntAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_start_date']


@admin.register(NotificationPlatform)
class NotificationPlatformAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'enabled']
    list_filter = ['type', 'enabled']
    search_fields = ['name']
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'enabled')
        }),
        (_('Configuration'), {
            'fields': ('config',),
            'classes': ('collapse',),
            'description': _('Platform-specific configuration (API keys, base URLs, etc.)')
        }),
    )


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'hunt', 'active']
    list_filter = ['platform', 'active', 'hunt']
    search_fields = ['user__email', 'user__display_name']
    raw_id_fields = ['user', 'hunt']
    fieldsets = (
        (None, {
            'fields': ('user', 'platform', 'hunt', 'active')
        }),
        (_('Notification Settings'), {
            'fields': ('event_types', 'destination'),
            'description': _('Event types to notify on and platform-specific destination')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'platform', 'hunt')

@admin.register(CannedHint)
class CannedHintAdmin(admin.ModelAdmin):
    list_display = ['puzzle', 'order', 'truncated_text']
    list_filter = ['puzzle__hunt', 'puzzle']
    search_fields = ['text', 'puzzle__name']
    ordering = ['puzzle', 'order']
    
    @admin.display(description="Hint Text")
    def truncated_text(self, obj):
        return truncatechars(obj.text, 100)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('puzzle', 'puzzle__hunt')

@admin.register(PuzzleFile)
class PuzzleFileAdmin(admin.ModelAdmin):
    pass

@admin.register(SolutionFile)
class SolutionFileAdmin(admin.ModelAdmin):
    pass

@admin.register(HuntFile)
class HuntFileAdmin(admin.ModelAdmin):
    pass

@admin.register(PrepuzzleFile)
class PrepuzzleFileAdmin(admin.ModelAdmin):
    pass