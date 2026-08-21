from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import DailyRatesForm, JewelleryItemForm
from .models import JewelleryItem, MetalRate


class ShopFilterMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.model, "shop"):
            qs = qs.select_related("shop")
        return qs.filter(shop=self.request.shop)


class ItemListView(LoginRequiredMixin, ShopFilterMixin, ListView):
    model = JewelleryItem
    template_name = "inventory/item_list.html"
    context_object_name = "items"

    def get_queryset(self):
        qs = super().get_queryset().select_related("category")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(item_name__icontains=q)
        return qs


class MetalRatesView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/metal_rates.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_shop_admin():
            messages.error(request, "Only shop admins can access and manage metal rates.")
            return redirect("dashboard:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.shop

        # Calculate current rates and fluctuations
        current_rates = {}
        rate_changes = {}
        for metal_code, _ in MetalRate.METAL_CHOICES:
            rates = MetalRate.objects.filter(shop=shop, metal_type=metal_code).order_by(
                "-effective_from", "-created_at"
            )[:2]
            rates_list = list(rates)
            if len(rates_list) > 0:
                current_rates[metal_code] = rates_list[0].rate_per_gram
                if len(rates_list) > 1:
                    rate_changes[metal_code] = rates_list[0].rate_per_gram - rates_list[1].rate_per_gram
                else:
                    rate_changes[metal_code] = 0.00
            else:
                current_rates[metal_code] = 0.00
                rate_changes[metal_code] = 0.00

        # Trend history logs for Chart.js
        history_qs = MetalRate.objects.filter(shop=shop).order_by("-effective_from")[:100]
        # Reverse to chronologically plot left to right
        history_list = []
        for rate in reversed(history_qs):
            history_list.append(
                {
                    "metal_type": rate.metal_type,
                    "rate": float(rate.rate_per_gram),
                    "date": rate.effective_from.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": rate.source,
                    "created_by": rate.created_by.username if rate.created_by else "System",
                }
            )

        # Table logs (most recent first)
        recent_logs = MetalRate.objects.filter(shop=shop).order_by("-effective_from", "-created_at")[:30]

        # Form pre-populated with current rates
        form = DailyRatesForm(
            initial={
                "gold_24k": current_rates.get("GOLD_24K"),
                "gold_22k": current_rates.get("GOLD_22K"),
                "gold_18k": current_rates.get("GOLD_18K"),
                "silver": current_rates.get("SILVER"),
            }
        )

        context.update(
            {
                "current_rates": current_rates,
                "rate_changes": rate_changes,
                "history_json": history_list,
                "recent_logs": recent_logs,
                "form": form,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        from core.services.permissions import PlanPermissionService

        if not PlanPermissionService.check(request.shop, "update_rates"):
            messages.error(request, "Your trial or subscription has expired. Please upgrade to unlock this feature.")
            return redirect("dashboard:home")

        form = DailyRatesForm(request.POST)
        if form.is_valid():
            effective_from = form.cleaned_data.get("effective_from")
            updated_count = 0

            # Map fields to metal choices
            field_mappings = {
                "gold_24k": "GOLD_24K",
                "gold_22k": "GOLD_22K",
                "gold_18k": "GOLD_18K",
                "silver": "SILVER",
            }

            for field_name, metal_code in field_mappings.items():
                rate_val = form.cleaned_data.get(field_name)
                if rate_val is not None:
                    # Create a new metal rate record
                    MetalRate.objects.create(
                        shop=request.shop,
                        metal_type=metal_code,
                        rate_per_gram=rate_val,
                        effective_from=effective_from,
                        created_by=request.user,
                    )
                    # Trigger updating JewelleryItems via bulk_update for efficiency
                    items = JewelleryItem.objects.filter(shop=request.shop, metal_type=metal_code)
                    bulk_items = []
                    for item in items:
                        item.metal_rate_used = rate_val
                        item.metal_cost = item.weight_in_grams * rate_val
                        item.price = item.metal_cost + item.making_charges + item.profit_margin
                        bulk_items.append(item)
                    if bulk_items:
                        JewelleryItem.objects.bulk_update(
                            bulk_items, ["metal_rate_used", "metal_cost", "price"], batch_size=100
                        )
                    updated_count += 1
            if updated_count > 0:
                messages.success(
                    request,
                    f"Successfully updated {updated_count} metal rate(s) and recalculated dependent jewellery prices!",
                )
            else:
                messages.warning(request, "No rate values were provided to update.")
            return redirect("inventory:metal_rates")

        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)


class ItemCreateView(LoginRequiredMixin, CreateView):
    model = JewelleryItem
    form_class = JewelleryItemForm
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")

    def dispatch(self, request, *args, **kwargs):
        from core.services.permissions import PlanPermissionService

        if not PlanPermissionService.check(request.shop, "create_product"):
            if hasattr(request, "subscription_locked") and request.subscription_locked:
                messages.error(
                    request, "Your trial or subscription has expired. Please upgrade to unlock this feature."
                )
                return redirect("dashboard:home")
            else:
                messages.error(
                    request,
                    "Product creation limit reached under your current subscription plan. Please upgrade your plan.",
                )
                return redirect("inventory:item_list")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["shop"] = self.request.shop
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rates = {}
        for m_code, _ in MetalRate.METAL_CHOICES:
            current_rate = MetalRate.get_current_rate(self.request.shop, m_code)
            rates[m_code] = float(current_rate) if current_rate else 0.0
        context["metal_rates_json"] = rates
        return context

    def form_valid(self, form):
        from .services.product import create_jewellery_item

        self.object = create_jewellery_item(
            shop=self.request.shop, data=form.cleaned_data, image_file=self.request.FILES.get("image")
        )
        return redirect(self.get_success_url())


class ItemUpdateView(LoginRequiredMixin, ShopFilterMixin, UpdateView):
    model = JewelleryItem
    form_class = JewelleryItemForm
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["shop"] = self.request.shop
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rates = {}
        for m_code, _ in MetalRate.METAL_CHOICES:
            current_rate = MetalRate.get_current_rate(self.request.shop, m_code)
            rates[m_code] = float(current_rate) if current_rate else 0.0
        context["metal_rates_json"] = rates
        return context

    def form_valid(self, form):
        from .services.product import update_jewellery_item

        self.object = update_jewellery_item(
            item=self.get_object(), data=form.cleaned_data, image_file=self.request.FILES.get("image")
        )
        return redirect(self.get_success_url())


class ItemDeleteView(LoginRequiredMixin, ShopFilterMixin, DeleteView):
    model = JewelleryItem
    success_url = reverse_lazy("inventory:item_list")
