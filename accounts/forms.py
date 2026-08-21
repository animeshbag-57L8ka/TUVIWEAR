
from django import forms
from django.contrib.auth.models import User

from .models import Profile


class RegisterForm(forms.ModelForm):

    real_name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your full name"
            }
        )
    )

    mobile = forms.CharField(
        max_length=15,
        label="Mobile Number",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your mobile number"
            }
        )
    )

    age = forms.IntegerField(
        min_value=13,
        max_value=100,
        label="Age",
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Enter your age"
            }
        )
    )

    gender = forms.ChoiceField(
        label="Gender",
        choices=Profile.GENDER_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "gender-select"
            }
        )
    )

    location = forms.CharField(
        max_length=200,
        label="Location",
        widget=forms.TextInput(
            attrs={
                "placeholder": "City / State"
            }
        )
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Create a password"
            }
        )
    )

    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm your password"
            }
        )
    )

    class Meta:
        model = User

        fields = [
            "username",
            "email",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Choose a username"
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Enter your email address"
                }
            ),
        }

    def clean_username(self):

        username = self.cleaned_data["username"]

        if User.objects.filter(
            username=username
        ).exists():

            raise forms.ValidationError(
                "This username is already taken."
            )

        return username

    def clean_email(self):

        email = self.cleaned_data["email"]

        if email and User.objects.filter(
            email=email
        ).exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_mobile(self):

        mobile = self.cleaned_data["mobile"]

        mobile = mobile.strip()

        if not mobile.isdigit():

            raise forms.ValidationError(
                "Mobile number must contain only digits."
            )

        if len(mobile) != 10:

            raise forms.ValidationError(
                "Enter a valid 10-digit mobile number."
            )

        return mobile

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")

        confirm_password = cleaned_data.get(
            "confirm_password"
        )

        if password and confirm_password:

            if password != confirm_password:

                self.add_error(
                    "confirm_password",
                    "Passwords do not match."
                )

        return cleaned_data

