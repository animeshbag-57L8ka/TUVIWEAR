from django import forms


class CheckoutForm(forms.Form):

    # =========================================================
    # FULL NAME
    # =========================================================

    full_name = forms.CharField(
        max_length=100,
        label="Full Name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your full name",
                "autocomplete": "name",
            }
        )
    )

    # =========================================================
    # EMAIL
    # =========================================================

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email",
                "autocomplete": "email",
            }
        )
    )

    # =========================================================
    # PHONE
    # =========================================================

    phone = forms.CharField(
        max_length=15,
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your phone number",
                "autocomplete": "tel",
                "inputmode": "numeric",
            }
        )
    )

    # =========================================================
    # ADDRESS
    # =========================================================

    address = forms.CharField(
        label="Delivery Address",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Enter your full delivery address",
                "autocomplete": "street-address",
                "rows": 4,
            }
        )
    )

    # =========================================================
    # CITY
    # =========================================================

    city = forms.CharField(
        max_length=100,
        label="City",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your city",
                "autocomplete": "address-level2",
            }
        )
    )

    # =========================================================
    # STATE
    # =========================================================

    state = forms.CharField(
        max_length=100,
        label="State",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your state",
                "autocomplete": "address-level1",
            }
        )
    )

    # =========================================================
    # PINCODE
    # =========================================================

    pincode = forms.CharField(
        max_length=10,
        label="PIN Code",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your PIN code",
                "autocomplete": "postal-code",
                "inputmode": "numeric",
            }
        )
    )

    # =========================================================
    # INITIAL DATA FROM USER PROFILE
    # =========================================================

    def __init__(self, *args, user=None, **kwargs):

        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:

            profile = getattr(
                user,
                "profile",
                None
            )

            # -------------------------------------------------
            # USERNAME / EMAIL
            # -------------------------------------------------

            if not self.is_bound:

                self.fields["email"].initial = user.email

            # -------------------------------------------------
            # PROFILE DATA
            # -------------------------------------------------

            if profile and not self.is_bound:

                self.fields[
                    "full_name"
                ].initial = profile.real_name

                self.fields[
                    "phone"
                ].initial = profile.mobile

                self.fields[
                    "address"
                ].initial = getattr(
                    profile,
                    "address",
                    ""
                )

                self.fields[
                    "city"
                ].initial = getattr(
                    profile,
                    "city",
                    ""
                )

                self.fields[
                    "state"
                ].initial = getattr(
                    profile,
                    "state",
                    ""
                )

                self.fields[
                    "pincode"
                ].initial = getattr(
                    profile,
                    "pincode",
                    ""
                )

    # =========================================================
    # PHONE VALIDATION
    # =========================================================

    def clean_phone(self):

        phone = self.cleaned_data["phone"].strip()

        if not phone.isdigit():

            raise forms.ValidationError(
                "Phone number must contain only digits."
            )

        if len(phone) != 10:

            raise forms.ValidationError(
                "Enter a valid 10-digit phone number."
            )

        return phone

    # =========================================================
    # PINCODE VALIDATION
    # =========================================================

    def clean_pincode(self):

        pincode = self.cleaned_data["pincode"].strip()

        if not pincode.isdigit():

            raise forms.ValidationError(
                "PIN code must contain only digits."
            )

        if len(pincode) != 6:

            raise forms.ValidationError(
                "Enter a valid 6-digit PIN code."
            )

        return pincode