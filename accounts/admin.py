from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'shop', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Shop Info', {'fields': ('shop', 'role', 'phone_number')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

