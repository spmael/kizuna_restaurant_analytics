from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Layout, Row, Submit
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserRegistrationForm(UserCreationForm):
    """Form for user registration."""

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label=_("First name"),
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label=_("Last name"),
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    restaurant_name = forms.CharField(
        label=_("Restaurant name"),
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label=_("Phone number"),
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "restaurant_name",
            "phone",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("email", css_class="form-group col-md-6 mb-3"),
                Column("username", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("first_name", css_class="form-group col-md-6 mb-3"),
                Column("last_name", css_class="form-group col-md-6 mb-3"),
            ),
            "restaurant_name",
            "phone",
            Row(
                Column("password1", css_class="form-group col-md-6 mb-3"),
                Column("password2", css_class="form-group col-md-6 mb-3"),
            ),
            HTML("<hr>"),
            Submit("submit", _("Create Account"), css_class="btn btn-primary btn-lg"),
        )

    def clean_email(self):
        """Check if the email is already in use."""
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("This email is already in use."))
        return email


class UserLoginForm(AuthenticationForm):
    """Form for user login."""

    username = forms.CharField(
        label=_("Email Address"),
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": _("Enter your email address"),
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": _("Enter your password"),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "username",
            "password",
            HTML(
                '<div class="text-right mb-3"><a href="{% url \'authentication:password_reset\' %}" class="text-muted">'
                + str(_("Forgot Password?"))
                + "</a></div>"
            ),
            Submit("submit", _("Login"), css_class="btn btn-primary btn-lg btn-block"),
        )


class UserProfileForm(forms.ModelForm):
    """Form for user profile."""

    first_name = forms.CharField(
        max_length=100,
        label=_("First name"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=100,
        label=_("Last name"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        max_length=254,
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    restaurant_name = forms.CharField(
        max_length=200,
        label=_("Restaurant name"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        max_length=20,
        label=_("Phone number"),
    )

    class Meta:
        model = UserProfile
        fields = ["bio", "timezone", "language", "receive_notifications"]
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "timezone": forms.Select(attrs={"class": "form-control"}),
            "language": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add user fields to the form
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
            self.fields["restaurant_name"].initial = self.instance.restaurant_name
            self.fields["phone"].initial = self.instance.phone

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<h4>" + str(_("Personal Information")) + "</h4><hr>"),
            Row(
                Column("first_name", css_class="form-group col-md-6 mb-3"),
                Column("last_name", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("email", css_class="form-group col-md-6 mb-3"),
                Column("phone", css_class="form-group col-md-6 mb-3"),
            ),
            "restaurant_name",
            "bio",
            HTML('<h4 class="mt-4">' + str(_("Preferences")) + "</h4><hr>"),
            Row(
                Column("timezone", css_class="form-group col-md-6 mb-3"),
                Column("language", css_class="form-group col-md-6 mb-3"),
            ),
            "receive_notifications",
            HTML("<hr>"),
            Submit("submit", _("Update Profile"), css_class="btn btn-primary"),
        )

    def save(self, commit=True):
        profile = super().save(commit=False)

        # Update user fields
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]

        # Update profile fields
        profile.restaurant_name = self.cleaned_data["restaurant_name"]
        profile.phone = self.cleaned_data["phone"]

        if commit:
            user.save()
            profile.save()

        return profile
