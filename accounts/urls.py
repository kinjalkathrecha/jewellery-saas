from django.contrib.auth import views as auth_views
from django.urls import path

from core.decorators import redis_rate_limit

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        redis_rate_limit("login", 5, 60)(auth_views.LoginView.as_view(template_name="accounts/login.html")),
        name="login",
    ),
    path(
        "password_reset/",
        redis_rate_limit("password_reset", 3, 3600)(auth_views.PasswordResetView.as_view()),
        name="password_reset",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.ShopSignupView.as_view(), name="register"),
    path("staff/", views.StaffListView.as_view(), name="staff_list"),
    path("staff/new/", views.StaffCreateView.as_view(), name="staff_add"),
]
