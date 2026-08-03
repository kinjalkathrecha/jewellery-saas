from django.db import models

from core.models import Shop


class Customer(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=20)
    city = models.CharField(max_length=100, blank=True, null=True)
    total_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.mobile_number}"
