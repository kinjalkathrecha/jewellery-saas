from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.ShopSignupView.as_view(), name='register'),
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/new/', views.StaffCreateView.as_view(), name='staff_add'),
]
