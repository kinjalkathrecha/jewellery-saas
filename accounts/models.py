from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
    )
    
    shop = models.ForeignKey('core.Shop', on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF')
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def is_shop_admin(self):
        return self.role == 'ADMIN'

