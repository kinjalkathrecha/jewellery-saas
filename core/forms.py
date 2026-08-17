from django import forms

from .models import Lead


class LeadForm(forms.ModelForm):
    # Honeypot field to detect automated spam submissions
    website = forms.CharField(required=False, widget=forms.HiddenInput(), label="Please leave blank")

    class Meta:
        model = Lead
        fields = [
            "name",
            "email",
            "phone",
            "shop_name",
            "message",
            "lead_type",
            "utm_source",
            "utm_medium",
            "utm_campaign",
        ]

    def clean_website(self):
        """
        If this honeypot field is filled, it's a bot submission.
        """
        website = self.cleaned_data.get("website")
        if website:
            raise forms.ValidationError("Anti-spam check failed.")
        return website

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.strip().lower()
        return email
