from django.forms import Form, CharField, TextInput
from allauth.account.forms import LoginForm
from django.conf import settings

class MyCustomSignupForm(Form):
    first_name = CharField(
        max_length=30,
        label='First name',
        widget = TextInput(
            attrs={"placeholder": "First Name"}
        ),
    )
    last_name = CharField(
        max_length=30,
        label='Last name',  # Fixed label that was incorrectly set to 'First name'
        widget = TextInput(
            attrs={"placeholder": "Last Name"}
        ),
    )
    display_name = CharField(
        max_length=40,
        label='Display name',
        widget=TextInput(
            attrs={"placeholder": "Display Name"}
        ),
    )

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.display_name = self.cleaned_data['display_name']
        user.save()


class ModifiedLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not bool(settings.EMAIL_CONFIGURED):
            self.fields['password'].help_text = "" 