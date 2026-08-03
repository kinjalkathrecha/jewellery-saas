from django import forms

from accounts.models import CustomUser
from customers.models import Customer

from .models import Repair


class RepairForm(forms.ModelForm):
    class Meta:
        model = Repair
        fields = [
            "customer",
            "item_category",
            "item_weight",
            "item_description",
            "item_photo",
            "repair_type",
            "priority",
            "estimated_cost",
            "actual_cost",
            "expected_delivery_date",
            "assigned_to",
            "status",
            "internal_notes",
        ]
        widgets = {
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "item_description": forms.Textarea(attrs={"rows": 3}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop("shop", None)
        super().__init__(*args, **kwargs)
        if shop:
            self.fields["customer"].queryset = Customer.objects.filter(shop=shop)
            self.fields["assigned_to"].queryset = CustomUser.objects.filter(shop=shop)

        # Add Bootstrap styling class to make form widgets look good
        for field_name, field in self.fields.items():
            if field_name not in ["item_photo"]:
                field.widget.attrs["class"] = "form-control"
