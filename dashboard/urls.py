from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('settings/', views.shop_settings, name='shop_settings'),
    path('reports/', views.business_reports_view, name='business_reports'),
]
