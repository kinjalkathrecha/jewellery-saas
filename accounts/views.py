from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import StaffCreationForm
from .models import CustomUser


class ShopAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_shop_admin()

    def handle_no_permission(self):
        messages.error(self.request, "Only shop admins can access this page.")
        return redirect("dashboard:home")


class StaffListView(LoginRequiredMixin, ShopAdminRequiredMixin, ListView):
    model = CustomUser
    template_name = "accounts/staff_list.html"
    context_object_name = "staff_list"

    def get_queryset(self):
        return CustomUser.objects.filter(shop=self.request.shop).exclude(id=self.request.user.id)


class StaffCreateView(LoginRequiredMixin, ShopAdminRequiredMixin, CreateView):
    model = CustomUser
    form_class = StaffCreationForm
    template_name = "accounts/staff_form.html"
    success_url = reverse_lazy("accounts:staff_list")

    def dispatch(self, request, *args, **kwargs):
        from core.services.permissions import PlanPermissionService

        if not PlanPermissionService.check(request.shop, "add_staff"):
            if hasattr(request, "subscription_locked") and request.subscription_locked:
                messages.error(
                    request, "Your trial or subscription has expired. Please upgrade to unlock this feature."
                )
                return redirect("dashboard:home")
            else:
                messages.error(
                    request,
                    "Staff member limit reached under your current subscription plan. Please upgrade your plan.",
                )
                return redirect("accounts:staff_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.shop = self.request.shop
        messages.success(self.request, "Staff member added successfully.")
        return super().form_valid(form)


from django.db import transaction
from django.views.generic import FormView

from core.models import Shop
from inventory.models import Category, MetalRate

from .forms import ShopSignupForm


class ShopSignupView(FormView):
    template_name = "accounts/register.html"
    form_class = ShopSignupForm
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # 1. Create the Shop
                shop = Shop.objects.create(
                    name=form.cleaned_data["shop_name"],
                    owner_name=form.cleaned_data["owner_name"],
                    email=form.cleaned_data["shop_email"],
                    phone_number=form.cleaned_data["shop_phone"],
                )

                # 2. Activate Free Trial subscription
                from core.services.subscription import activate_subscription

                activate_subscription(shop=shop, plan=form.cleaned_data["subscription_plan"], is_trial=True)

                # 2. Create the Admin user
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["admin_email"],
                    password=form.cleaned_data["password"],
                    shop=shop,
                    role="ADMIN",
                )

                # 3. Seed default Categories for new shop
                Category.objects.create(shop=shop, name="Gold Rings", description="Standard 22K/18K Gold Rings")
                Category.objects.create(
                    shop=shop, name="Diamond Necklaces", description="Exquisite Diamond and Precious Stone Necklaces"
                )

                # 4. Seed default Metal Rates
                rates_data = [
                    ("GOLD_24K", 7000.00),
                    ("GOLD_22K", 6500.00),
                    ("GOLD_18K", 5400.00),
                    ("SILVER", 90.00),
                ]
                for m_type, rate in rates_data:
                    MetalRate.objects.create(
                        shop=shop, metal_type=m_type, rate_per_gram=rate, source="MANUAL", created_by=user
                    )

            messages.success(
                self.request, "Your shop registration was successful! Please log in to access your dashboard."
            )
            return super().form_valid(form)

        except Exception as e:
            form.add_error(None, f"An error occurred during registration: {e!s}")
            return self.form_invalid(form)
