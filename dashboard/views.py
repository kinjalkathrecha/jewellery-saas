from django.contrib.auth.decorators import login_required
from django.db.models import Avg, DurationField, ExpressionWrapper, F, Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.shortcuts import render
from django.utils import timezone

from accounts.models import CustomUser
from billing.models import Invoice
from core.services import cache_service
from customers.models import Customer
from inventory.models import JewelleryItem
from repairs.models import Repair


@receiver([post_save, post_delete], sender=JewelleryItem)
@receiver([post_save, post_delete], sender=Invoice)
@receiver([post_save, post_delete], sender=Customer)
@receiver([post_save, post_delete], sender=Repair)
@receiver([post_save, post_delete], sender=CustomUser)
def invalidate_dashboard_cache(sender, instance, **kwargs):
    shop_id = getattr(instance, "shop_id", None)
    if shop_id:
        cache_service.invalidate_dashboard(shop_id)

@login_required
def home(request):
    shop = request.shop

    cached_context = cache_service.get_dashboard_stats(shop.id)
    if cached_context is not None:
        # Dynamically refresh active subscription object from current request context
        cached_context["sub"] = shop.active_subscription
        return render(request, "dashboard/home.html", cached_context)

    # Context stats
    total_products = JewelleryItem.objects.filter(shop=shop).count()
    total_customers = Customer.objects.filter(shop=shop).count()

    # Today's sales (simplified to all invoices for now)
    total_sales = Invoice.objects.filter(shop=shop).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    low_stock_query = JewelleryItem.objects.filter(shop=shop, stock_quantity__lte=5)
    low_stock_count = low_stock_query.count()
    low_stock_items = list(low_stock_query[:5])
    recent_invoices = list(Invoice.objects.filter(shop=shop).select_related("customer").order_by("-created_at")[:5])

    # Repairs Stats
    repairs_pending = Repair.objects.filter(shop=shop, status__in=["RECEIVED", "UNDER_REPAIR"], is_active=True).count()
    repairs_ready = Repair.objects.filter(shop=shop, status="READY", is_active=True).count()
    repairs_delivered_today = Repair.objects.filter(
        shop=shop, status="DELIVERED", delivered_at__date=timezone.now().date(), is_active=True
    ).count()
    repairs_overdue = (
        Repair.objects.filter(shop=shop, is_active=True)
        .exclude(status__in=["DELIVERED", "CANCELLED"])
        .filter(expected_delivery_date__lt=timezone.now().date())
        .count()
    )

    # Repairs Revenue
    revenue_today = (
        Repair.objects.filter(
            shop=shop, status="DELIVERED", delivered_at__date=timezone.now().date(), actual_cost__gt=0, is_active=True
        ).aggregate(Sum("actual_cost"))["actual_cost__sum"]
        or 0
    )
    revenue_month = (
        Repair.objects.filter(
            shop=shop,
            status="DELIVERED",
            delivered_at__year=timezone.now().year,
            delivered_at__month=timezone.now().month,
            actual_cost__gt=0,
            is_active=True,
        ).aggregate(Sum("actual_cost"))["actual_cost__sum"]
        or 0
    )

    # Repairs Completion Duration
    delivered_repairs = Repair.objects.filter(shop=shop, status="DELIVERED", delivered_at__isnull=False, is_active=True)
    if delivered_repairs.exists():
        avg_duration = delivered_repairs.annotate(
            duration=ExpressionWrapper(F("delivered_at") - F("created_at"), output_field=DurationField())
        ).aggregate(Avg("duration"))["duration__avg"]
        if avg_duration:
            avg_completion_days = round(avg_duration.total_seconds() / (24 * 3600), 1)
        else:
            avg_completion_days = 0
    else:
        avg_completion_days = 0

    # Subscription status and plan limits
    sub = shop.active_subscription
    max_products = sub.max_products if sub else 1000
    max_users = sub.max_users if sub else 3
    max_invoices = sub.max_invoices_per_month if sub else 1000

    # Staff count (total users under shop)
    total_staff = CustomUser.objects.filter(shop=shop).count()

    # Monthly invoice count
    total_invoices_month = Invoice.objects.filter(
        shop=shop, created_at__year=timezone.now().year, created_at__month=timezone.now().month
    ).count()

    # Usage percentages (for progress bar)
    prod_percent = min(100, int((total_products / max_products) * 100)) if max_products > 0 else 0
    staff_percent = min(100, int((total_staff / max_users) * 100)) if max_users > 0 else 0
    invoice_percent = min(100, int((total_invoices_month / max_invoices) * 100)) if max_invoices > 0 else 0

    context = {
        "total_products": total_products,
        "total_customers": total_customers,
        "total_sales": total_sales,
        "low_stock_count": low_stock_count,
        "low_stock_items": low_stock_items,
        "recent_invoices": recent_invoices,
        "repairs_pending": repairs_pending,
        "repairs_ready": repairs_ready,
        "repairs_delivered_today": repairs_delivered_today,
        "repairs_overdue": repairs_overdue,
        "revenue_today": revenue_today,
        "revenue_month": revenue_month,
        "avg_completion_days": avg_completion_days,
        # Subscription usage context
        "sub": sub,
        "max_products": max_products,
        "max_users": max_users,
        "max_invoices": max_invoices,
        "total_staff": total_staff,
        "total_invoices_month": total_invoices_month,
        "prod_percent": prod_percent,
        "staff_percent": staff_percent,
        "invoice_percent": invoice_percent,
    }
    cache_service.set_dashboard_stats(shop.id, context)
    return render(request, "dashboard/home.html", context)



from django.contrib import messages
from django.shortcuts import redirect

from .forms import ShopSettingsForm


@login_required
def shop_settings(request):
    if not request.user.is_shop_admin():
        messages.error(request, "Only shop admins can access settings.")
        return redirect("dashboard:home")

    shop = request.shop
    if request.method == "POST":
        form = ShopSettingsForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully!")
            return redirect("dashboard:shop_settings")
    else:
        form = ShopSettingsForm(instance=shop)

    return render(request, "dashboard/shop_settings.html", {"form": form})


@login_required
def business_reports_view(request):
    """
    Renders business analytics, sales distributions, gold/silver breakdowns,
    and transaction growth charts.
    """
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    from django.utils import timezone

    from billing.models import Invoice, InvoiceItem
    from repairs.models import Repair

    shop = request.shop

    # 1. High-Level KPIs
    total_sales_count = Invoice.objects.filter(shop=shop).count()
    total_revenue = Invoice.objects.filter(shop=shop).aggregate(Sum("total_amount"))["total_amount__sum"] or 0.00
    aov = total_revenue / total_sales_count if total_sales_count > 0 else 0.00

    total_repairs_count = Repair.objects.filter(shop=shop, is_active=True).count()
    completed_repairs = Repair.objects.filter(shop=shop, status="DELIVERED", is_active=True).count()
    repairs_revenue = (
        Repair.objects.filter(shop=shop, status="DELIVERED", is_active=True).aggregate(Sum("actual_cost"))[
            "actual_cost__sum"
        ]
        or 0.00
    )

    # 2. Metal Distribution (Doughnut Chart Data)
    metal_data = (
        InvoiceItem.objects.filter(invoice__shop=shop, item__isnull=False)
        .values("item__metal_type")
        .annotate(qty=Sum("quantity"), sales=Sum("amount"))
    )

    metal_labels = []
    metal_values = []
    metal_colors = []

    color_map = {
        "GOLD_24K": "#FFD700",  # Pure Gold
        "GOLD_22K": "#DAA520",  # Goldenrod
        "GOLD_18K": "#B8860B",  # Dark Goldenrod
        "SILVER": "#C0C0C0",  # Silver
        "FIXED": "#94a3b8",  # Slate
    }

    label_map = {
        "GOLD_24K": "Gold 24K",
        "GOLD_22K": "Gold 22K",
        "GOLD_18K": "Gold 18K",
        "SILVER": "Silver",
        "FIXED": "Fixed Price (Manual)",
    }

    for item in metal_data:
        m_type = item["item__metal_type"]
        metal_labels.append(label_map.get(m_type, m_type))
        metal_values.append(float(item["sales"] or 0))
        metal_colors.append(color_map.get(m_type, "#475569"))

    # 3. Monthly Sales & Repair Trends (Bar Chart Data)
    now = timezone.now()
    monthly_sales = (
        Invoice.objects.filter(shop=shop, created_at__year=now.year)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(val=Sum("total_amount"))
        .order_by("month")
    )

    monthly_repairs = (
        Repair.objects.filter(shop=shop, status="DELIVERED", is_active=True, delivered_at__year=now.year)
        .annotate(month=TruncMonth("delivered_at"))
        .values("month")
        .annotate(val=Sum("actual_cost"))
        .order_by("month")
    )

    months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sales_trend = [0.0] * 12
    repairs_trend = [0.0] * 12

    for item in monthly_sales:
        m_idx = item["month"].month - 1
        sales_trend[m_idx] = float(item["val"] or 0)

    for item in monthly_repairs:
        m_idx = item["month"].month - 1
        repairs_trend[m_idx] = float(item["val"] or 0)

    # 4. Top Selling Items List
    top_selling = (
        InvoiceItem.objects.filter(invoice__shop=shop, item__isnull=False)
        .values("item__item_name", "item__design_code", "item__price")
        .annotate(total_qty=Sum("quantity"), total_rev=Sum("amount"))
        .order_by("-total_qty")[:5]
    )

    context = {
        "total_sales_count": total_sales_count,
        "total_revenue": total_revenue,
        "aov": aov,
        "total_repairs_count": total_repairs_count,
        "completed_repairs": completed_repairs,
        "repairs_revenue": repairs_revenue,
        # Chart payloads
        "metal_labels": metal_labels,
        "metal_values": metal_values,
        "metal_colors": metal_colors,
        "months_labels": months_labels,
        "sales_trend": sales_trend,
        "repairs_trend": repairs_trend,
        "top_selling": top_selling,
    }
    return render(request, "dashboard/reports.html", context)
