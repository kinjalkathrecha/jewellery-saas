from django import forms
from django.utils import timezone

from .models import Category, JewelleryItem


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

class JewelleryItemForm(forms.ModelForm):
    class Meta:
        model = JewelleryItem
        fields = [
            'item_name', 'category', 'metal_type', 'weight_in_grams', 
            'making_charges', 'profit_margin', 'price', 'stock_quantity', 
            'design_code', 'barcode_type', 'image'
        ]

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)
        if shop:
            self.fields['category'].queryset = Category.objects.filter(shop=shop)
            # Make price field not strictly required if dynamic pricing is selected,
            # as it will be calculated on save.
            self.fields['price'].required = False

class DailyRatesForm(forms.Form):
    gold_24k = forms.DecimalField(
        label="Gold 24K (₹/g)", 
        max_digits=10, decimal_places=2, 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter rate'})
    )
    gold_22k = forms.DecimalField(
        label="Gold 22K (₹/g)", 
        max_digits=10, decimal_places=2, 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter rate'})
    )
    gold_18k = forms.DecimalField(
        label="Gold 18K (₹/g)", 
        max_digits=10, decimal_places=2, 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter rate'})
    )
    silver = forms.DecimalField(
        label="Silver (₹/g)", 
        max_digits=10, decimal_places=2, 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter rate'})
    )
    effective_from = forms.DateTimeField(
        label="Effective From", 
        initial=timezone.now, 
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )

