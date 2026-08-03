from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.models import Shop, SubscriptionPlan

from .models import CustomUser


class StaffCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "phone_number", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit role choices to STAFF if needed, but since it's an admin creating it, they might want either.
        # It's safer to only allow STAFF creation from this form by setting choices or defaulting it
        self.fields["role"].choices = [("STAFF", "Staff")]
        self.fields["role"].initial = "STAFF"


class ShopSignupForm(forms.Form):
    # Shop fields
    shop_name = forms.CharField(
        max_length=255, label="Shop Name", widget=forms.TextInput(attrs={"placeholder": "e.g. Shreem Jewellers"})
    )
    owner_name = forms.CharField(
        max_length=255, label="Owner Name (Your Name)", widget=forms.TextInput(attrs={"placeholder": "Your Full Name"})
    )
    shop_email = forms.EmailField(
        label="Shop Email Address", widget=forms.EmailInput(attrs={"placeholder": "contact@yourshop.com"})
    )
    shop_phone = forms.CharField(
        max_length=20, label="Shop Phone Number", widget=forms.TextInput(attrs={"placeholder": "e.g. 9876543210"})
    )
    subscription_plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.all(),
        required=True,
        label="Choose Subscription Plan",
        empty_label="Select a plan...",
    )

    # User fields
    username = forms.CharField(
        max_length=150,
        label="Admin Username",
        widget=forms.TextInput(attrs={"placeholder": "Choose a username for login"}),
    )
    admin_email = forms.EmailField(
        label="Admin Personal Email", widget=forms.EmailInput(attrs={"placeholder": "yourname@email.com"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Choose a secure password"}), label="Password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat password"}), label="Confirm Password"
    )

    def clean_shop_email(self):
        email = self.cleaned_data.get("shop_email")
        if Shop.objects.filter(email=email).exists():
            raise forms.ValidationError("A shop with this email address is already registered.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned_data
