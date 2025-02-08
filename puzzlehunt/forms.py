import re

from crispy_bulma.layout import Submit, FormGroup
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div
from django.conf import settings
from django.forms import (
    ModelForm, Form, CharField, FileField, 
    TextInput, MultipleChoiceField, CheckboxSelectMultiple
)
from django.contrib.auth.forms import ValidationError
from django.urls import reverse

from .models import Team, User, NotificationSubscription, Event
from .notifications import NotificationHandler

class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'is_local']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.helper.layout = Layout(
            'name',
            Div(
                Div(Field('is_local', template="components/_bulma_rounded_checkbox.html"), css_class="level-left"),
                Div(Submit(button_text, button_text, css_class="is-primary"), css_class="level-right"),
                css_class="level"
            ),
        )

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
