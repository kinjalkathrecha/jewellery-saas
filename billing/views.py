from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from inventory.models import JewelleryItem

from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice


class ShopFilterMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.model, "shop"):
            qs = qs.select_related("shop")
        return qs.filter(shop=self.request.shop)


class InvoiceListView(LoginRequiredMixin, ShopFilterMixin, ListView):
    model = Invoice
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().select_related("customer")


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "billing/invoice_form.html"

    def dispatch(self, request, *args, **kwargs):
        from core.services.permissions import PlanPermissionService

        if not PlanPermissionService.check(request.shop, "create_invoice"):
            if hasattr(request, "subscription_locked") and request.subscription_locked:
                messages.error(
                    request, "Your trial or subscription has expired. Please upgrade to unlock this feature."
                )
            else:
                messages.error(
                    request,
                    "Monthly invoice limit reached under your current subscription plan. Please upgrade your plan.",
                )
            return redirect("billing:invoice_list")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("billing:invoice_detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["shop"] = self.request.shop
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            formset = InvoiceItemFormSet(self.request.POST)
            for form in formset.forms:
                form.fields["item"].queryset = JewelleryItem.objects.filter(shop=self.request.shop)
            data["items"] = formset
        else:
            formset = InvoiceItemFormSet()
            for form in formset.forms:
                form.fields["item"].queryset = JewelleryItem.objects.filter(shop=self.request.shop)
            data["items"] = formset
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]

        form.instance.shop = self.request.shop

        if form.is_valid() and items.is_valid():
            from django.db import transaction
            with transaction.atomic():
                self.object = form.save()

                # Save invoice items using commit=False to set the rate audit field
                invoice_items = items.save(commit=False)
                subtotal = 0
                for item in invoice_items:
                    item.invoice = self.object

                    # Fetch and store today's metal rate for audit
                    if item.item and item.item.metal_type != "FIXED":
                        from inventory.models import MetalRate

                        rate_val = MetalRate.get_current_rate(self.request.shop, item.item.metal_type)
                        if rate_val:
                            item.invoice_metal_rate = rate_val

                    item.save()
                    subtotal += item.amount

                    # Logic to deduct stock
                    if item.item:
                        item.item.stock_quantity -= item.quantity
                        item.item.save()

                items.save_m2m()

                self.object.subtotal = subtotal
                self.object.total_amount = subtotal + self.object.tax_amount
                self.object.save()

                # Update customer total spent
                if self.object.customer:
                    self.object.customer.total_spent += self.object.total_amount
                    self.object.customer.save()

            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class InvoiceDetailView(LoginRequiredMixin, ShopFilterMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("customer").prefetch_related("items__item")


def get_item_price(request):
    """AJAX endpoint to get item price for dynamic JS updating"""
    item_id = request.GET.get("item_id")
    if item_id:
        item = get_object_or_404(JewelleryItem, id=item_id, shop=request.user.shop)
        current_price = item.get_current_price()
        return JsonResponse({"rate": float(current_price)})
    return JsonResponse({"rate": 0})


@login_required
def invoice_pdf_view(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, shop=request.shop)
    return render(request, "billing/invoice_pdf.html", {"invoice": invoice, "shop": request.shop, "request": request})


@login_required
def billing_subscription_view(request):
    """
    Displays current subscription details, snapshots, limits, plans, and payment logs.
    """
    from django.utils import timezone

    from core.models import Subscription, SubscriptionPlan

    plans = SubscriptionPlan.objects.all()
    history = Subscription.objects.filter(shop=request.shop).order_by("-created_at")

    # Calculate limits/usage variables
    total_products = JewelleryItem.objects.filter(shop=request.shop).count()
    from accounts.models import CustomUser

    total_staff = CustomUser.objects.filter(shop=request.shop).count()
    total_invoices_month = Invoice.objects.filter(
        shop=request.shop, created_at__year=timezone.now().year, created_at__month=timezone.now().month
    ).count()

    context = {
        "plans": plans,
        "active_sub": request.shop.active_subscription,
        "history": history,
        "status_info": request.subscription_status,
        "total_products": total_products,
        "total_staff": total_staff,
        "total_invoices_month": total_invoices_month,
    }
    return render(request, "billing/subscription.html", context)


@login_required
def upgrade_subscription_view(request):
    """
    Handles payment transaction triggers, updating plan records.
    """
    from django.utils import timezone

    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        from core.models import SubscriptionPlan

        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        # Simulate payment processor signature validation
        payment_ref = request.POST.get("payment_reference") or f"PAY-SIM-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        gateway_order_id = request.POST.get("gateway_order_id") or f"order_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        gateway_payment_id = request.POST.get("gateway_payment_id") or f"pay_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        gateway_signature = request.POST.get("gateway_signature") or "sig_validated"

        from core.services.subscription import activate_subscription

        activate_subscription(
            shop=request.shop,
            plan=plan,
            is_trial=False,
            amount=plan.price,
            payment_ref=payment_ref,
            gateway_order_id=gateway_order_id,
            gateway_payment_id=gateway_payment_id,
            gateway_signature=gateway_signature,
        )

        messages.success(request, f"Successfully upgraded to {plan.name}! All limits refreshed.")
        return redirect("billing:subscription_details")
    return redirect("billing:subscription_details")
