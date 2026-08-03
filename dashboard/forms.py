from django import forms

from core.models import Shop


class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = [
            "name",
            "owner_name",
            "phone_number",
            "address",
            "gstin",
            "logo",
            "sku_prefix",
            "scanner_suffix",
            "terms_and_conditions",
        ]
        widgets = {
            "terms_and_conditions": forms.Textarea(attrs={"rows": 4}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }
