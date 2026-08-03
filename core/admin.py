from django.contrib import admin

from .models import Shop, SubscriptionPlan

admin.site.register(SubscriptionPlan)
admin.site.register(Shop)
