import re

from crispy_bulma.layout import Submit, FormGroup, Field as BulmaField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div
from django.conf import settings
from django.forms import (
    ModelForm, Form, CharField, FileField, ChoiceField,
    TextInput, MultipleChoiceField, CheckboxSelectMultiple,
    BooleanField, CheckboxInput
)
from django.contrib.auth.forms import ValidationError
from django.urls import reverse

from .models import Team, User, NotificationSubscription, Event, TeamDataQuestion, TeamDataAnswer
from .notifications import NotificationHandler

class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ['name']

    def __init__(self, *args, hunt=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hunt = hunt or (self.instance.hunt if self.instance.hunt_id else None)
        self.helper = FormHelper()
        if self.instance.pk:
            url = reverse("puzzlehunt:team_update", kwargs={'pk': self.instance.pk})
            button_text = "Update"
            self.helper.attrs = {'hx-post': reverse('puzzlehunt:team_update', kwargs={'pk': self.instance.pk})}
        else:
            url = reverse("puzzlehunt:team_create")
            button_text = "Register"
        self.helper.form_class = 'block'
        self.helper.form_action = url

        self.questions = (
            list(self.hunt.teamdataquestion_set.order_by('question_order')) if self.hunt else []
        )
        existing_answers = (
            {a.question_id: a.value for a in self.instance.teamdataanswer_set.all()}
            if self.instance.pk else {}
        )

        layout_fields = ['name']
        for question in self.questions:
            field_name = f'question_{question.pk}'
            if question.question_type == TeamDataQuestion.QuestionType.BOOLEAN:
                self.fields[field_name] = BooleanField(
                    required=question.required,
                    label=question.name,
                    help_text=question.description,
                )
                if question.pk in existing_answers:
                    self.initial[field_name] = existing_answers[question.pk] == 'True'
                switch_field = BulmaField(
                    field_name,
                    template='components/_bulma_switch_field.html',
                    wrapper_class='field'
                )
                layout_fields.append(
                    Div(Div(switch_field, css_class="level-left"), css_class="level")
                )
            elif question.question_type == TeamDataQuestion.QuestionType.SELECT:
                choices = ([('', '---')] if not question.required else []) + [
                    (opt, opt) for opt in question.options
                ]
                self.fields[field_name] = ChoiceField(
                    required=question.required,
                    label=question.name,
                    help_text=question.description,
                    choices=choices,
                )
                if question.pk in existing_answers:
                    self.initial[field_name] = existing_answers[question.pk]
                layout_fields.append(
                    Div(Div(Field(field_name), css_class="level-left"), css_class="level")
                )
            else:
                self.fields[field_name] = CharField(
                    required=question.required,
                    label=question.name,
                    help_text=question.description,
                    max_length=200,
                )
                if question.pk in existing_answers:
                    self.initial[field_name] = existing_answers[question.pk]
                layout_fields.append(
                    Div(Div(Field(field_name), css_class="level-left"), css_class="level")
                )

        layout_fields.append(
            Div(
                Div(Submit(button_text, button_text, css_class="is-primary"), css_class="level-right"),
                css_class="level"
            )
        )
        self.helper.layout = Layout(*layout_fields)

    def clean_name(self):
        instance = getattr(self, 'instance', None)
        name = self.cleaned_data.get('name')

        if not instance:
            return name

        if name != instance.name:
            if instance.hunt.team_set.filter(name__iexact=name).exists():
                raise ValidationError('Another team is already using that name.')

        if not re.match(r".*[A-Za-z0-9].*", name):
            raise ValidationError('A team name must contain at least one alphanumeric character.')

        return name

    def save(self, commit=True):
        team = super().save(commit=commit)
        if commit:
            for question in self.questions:
                raw = self.cleaned_data.get(f'question_{question.pk}')
                if question.question_type == TeamDataQuestion.QuestionType.BOOLEAN:
                    value = str(bool(raw))
                else:
                    value = raw or ''
                TeamDataAnswer.objects.update_or_create(
                    team=team, question=question, defaults={'value': value}
                )
        return team


class TeamDataQuestionForm(ModelForm):
    options = CharField(
        required=False,
        help_text='Comma-separated list of choices. Only used when Type is "Select".',
    )

    class Meta:
        model = TeamDataQuestion
        fields = ['name', 'description', 'question_type', 'required', 'visible_on_leaderboard', 'used_for_grouping']

    def __init__(self, *args, hunt=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hunt = hunt or (self.instance.hunt if self.instance.hunt_id else None)

        if self.instance.pk:
            self.initial['options'] = ', '.join(self.instance.options)
            url = reverse('puzzlehunt:staff:team_data_question_update', args=[self.hunt.pk, self.instance.pk])
        else:
            url = reverse('puzzlehunt:staff:team_data_question_create', args=[self.hunt.pk])

        self.helper = FormHelper()
        self.helper.form_class = 'block'
        self.helper.attrs = {'hx-post': url, 'hx-target': '#team-data-question-list', 'hx-swap': 'innerHTML'}
        self.helper.form_action = url
        self.helper.layout = Layout(
            Field('name'),
            Field('description'),
            Field('question_type'),
            Field('options'),
            Field('required'),
            Field('visible_on_leaderboard'),
            Field('used_for_grouping'),
            Div(Div(Submit('save', 'Save', css_class="is-primary"), css_class="level-right"), css_class="level"),
        )

    def clean_options(self):
        raw = self.cleaned_data.get('options', '')
        return [opt.strip() for opt in raw.replace('\n', ',').split(',') if opt.strip()]

    def clean(self):
        cleaned_data = super().clean()
        # Non-select questions never store options, regardless of stray text left in the field
        if cleaned_data.get('question_type') != TeamDataQuestion.QuestionType.SELECT:
            cleaned_data['options'] = []
        return cleaned_data

    def _post_clean(self):
        # `options` is a plain CharField proxying the model's JSONField, so it isn't in
        # Meta.fields and Django's ModelForm machinery won't copy it onto the instance for
        # us. Set it before super()._post_clean() runs instance.full_clean(), so
        # TeamDataQuestion.clean()'s select/options cross-check sees the right value and can
        # attach its error to this form's `options` field.
        self.instance.options = self.cleaned_data.get('options', [])
        super()._post_clean()


class UserEditForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'block'
        self.helper.attrs = {'hx-patch': reverse('puzzlehunt:user_detail_view')}
        self.helper.layout = Layout(
            Field('display_name'),
            Div(Div('first_name', 'last_name', css_class="field-body"), css_class="field is-horizontal"),
            FormGroup(Submit('Update', 'Update', css_class="is-primary"), css_class="is-grouped-right")
        )

    class Meta:
        model = User
        fields = ['display_name', 'first_name', 'last_name']


class MediaUploadForm(Form):
    model_type = CharField()
    model_id = CharField()
    file = FileField()


class AnswerForm(Form):
    answer = CharField(max_length=100, label='Answer')

    def __init__(self, *args, **kwargs):
        disable_form = kwargs.pop('disable_form', False)
        is_prepuzzle = kwargs.pop('is_prepuzzle', False)
        self.puzzle = kwargs.pop('puzzle')
        super(AnswerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "block"
        if is_prepuzzle:
            view = 'puzzlehunt:prepuzzle_submit'
        else:
            view = 'puzzlehunt:puzzle_submit'
        url = reverse(view, kwargs={'pk': self.puzzle.pk})
        self.helper.attrs = {'hx-post': url, 'hx-swap': 'outerHTML'}
        self.helper.form_action = url
        if disable_form:
            # noinspection PyTypeChecker
            self.helper.layout = Layout(
                FormGroup(
                    Field('answer', placeholder="Answer", readonly=disable_form,
                          template="components/_bulma_expanded_text_input.html"),
                    Submit('Submit', value="submit", type="submit", disabled="disabled", css_class="is-primary")
                )
            )
        else:
            # noinspection PyTypeChecker
            self.helper.layout = Layout(
                FormGroup(
                    Field('answer', placeholder="Answer", template="components/_bulma_expanded_text_input.html"),
                    Submit('Submit', value="Submit", type="submit", css_class="is-primary")
                )
            )

    def clean_answer(self):
        data = self.cleaned_data['answer']
        original_answer = data
        puzzle = self.puzzle
        if not puzzle.allow_spaces:
            data = re.sub(r'\s+', '', data)
        if not puzzle.allow_non_alphanumeric:
            data = re.sub(r'[^A-Za-z0-9]', '', data)
        if not puzzle.case_sensitive:
            data = data.lower()
        # Note: A check here for orginal_answer != answer would allow erroring instead of modifying the answer

        return data


class NotificationSubscriptionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'block'
        self.helper.attrs = {'hx-post': reverse('puzzlehunt:notification_view')}
        
        event_choices = [(et.value, et.label) for et in Event.public_types]
        self.fields['event_types'] = MultipleChoiceField(
            choices=event_choices,
            widget=CheckboxSelectMultiple,
            required=True,
            help_text="Select which events you want to be notified about"
        )
        
        self.helper.layout = Layout(
            Field('platform'),
            Field('hunt'),
            Field('event_types'),
            Field('destination'),
            Field('active', type='hidden', initial=True),
            FormGroup(Submit('Create', 'Create', css_class="is-primary"), 
                     css_class="is-grouped-right")
        )

    def clean(self):
        cleaned_data = super().clean()
        platform = cleaned_data.get('platform')
        destination = cleaned_data.get('destination', '')  # Default to empty string if not provided

        if platform:
            handler = NotificationHandler.create_handler(platform)
            if handler:
                try:
                    handler.validate_destination(destination)
                except ValidationError as e:
                    self.add_error('destination', e)

        return cleaned_data

    def clean_event_types(self):
        """Convert list of selected events into comma-separated string"""
        return ','.join(self.cleaned_data['event_types'])

    class Meta:
        model = NotificationSubscription
        fields = ['platform', 'hunt', 'event_types', 'destination', 'active']
