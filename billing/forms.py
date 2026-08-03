from django import forms
from django.forms import inlineformset_factory

from customers.models import Customer
from inventory.models import JewelleryItem

from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["customer", "invoice_number", "tax_amount"]

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop("shop", None)
        super().__init__(*args, **kwargs)
        if shop:
            self.fields["customer"].queryset = Customer.objects.filter(shop=shop)


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["item", "quantity", "rate", "amount"]

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop("shop", None)
        super().__init__(*args, **kwargs)
        if shop:
            self.fields["item"].queryset = JewelleryItem.objects.filter(shop=shop)


# Base formset factory
InvoiceItemFormSet = inlineformset_factory(Invoice, InvoiceItem, form=InvoiceItemForm, extra=1, can_delete=True)
