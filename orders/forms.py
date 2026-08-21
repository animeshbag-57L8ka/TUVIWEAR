
from django import forms


class CheckoutForm(forms.Form):

    full_name = forms.CharField(
        max_length=100,
        label="Full Name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your full name",
                "class": "form-control"
            }
        )
    )

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email",
                "class": "form-control"
            }
        )
    )

    phone = forms.CharField(
        max_length=15,
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your phone number",
                "class": "form-control"
            }
        )
    )

    address = forms.CharField(
        label="Address",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Enter your full address",
                "class": "form-control",
                "rows": 4
            }
        )
    )

    city = forms.CharField(
        max_length=100,
        label="City",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your city",
                "class": "form-control"
            }
        )
    )

    state = forms.CharField(
        max_length=100,
        label="State",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your state",
                "class": "form-control"
            }
        )
    )

    pincode = forms.CharField(
        max_length=10,
        label="PIN Code",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your PIN code",
                "class": "form-control"
            }
        )
    )

