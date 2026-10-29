from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


def add_bootstrap_class(form):
    """Give every field in the form the Bootstrap 'form-control' style."""
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")


class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["email"].required = True
        self.fields["phone"].required = True
        self.fields["address"].required = True
        add_bootstrap_class(self)


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_class(self)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_class(self)