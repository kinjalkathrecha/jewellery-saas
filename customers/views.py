from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CustomerForm
from .models import Customer


class ShopFilterMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.model, "shop"):
            qs = qs.select_related("shop")
        return qs.filter(shop=self.request.shop)


class CustomerListView(LoginRequiredMixin, ShopFilterMixin, ListView):
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(mobile_number__icontains=q)
        return qs


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")

    def dispatch(self, request, *args, **kwargs):
        from core.services.permissions import PlanPermissionService

        if not PlanPermissionService.check(request.shop, "create_customer"):
            messages.error(request, "Your trial or subscription has expired. Please upgrade to unlock this feature.")
            return redirect("customers:customer_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.shop = self.request.shop
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, ShopFilterMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")


class CustomerDeleteView(LoginRequiredMixin, ShopFilterMixin, DeleteView):
    model = Customer
    success_url = reverse_lazy("customers:customer_list")
