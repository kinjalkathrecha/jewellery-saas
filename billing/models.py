from django.db import models

from core.models import Shop
from customers.models import Customer
from inventory.models import JewelleryItem


class Invoice(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='invoices')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(auto_now_add=True)
    
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) # e.g. 3% GST
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.invoice_number}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(JewelleryItem, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    rate = models.DecimalField(max_digits=15, decimal_places=2) # snapshot of price + making charges
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    invoice_metal_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} x {getattr(self.item, 'item_name', 'Deleted Item')} for {self.invoice.invoice_number}"


