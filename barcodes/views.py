import uuid

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from inventory.models import JewelleryItem

from .models import BarcodeEvent, LabelTemplate


@login_required
def print_tags_view(request):
    """
    Renders the print preview layout for single or bulk jewellery items.
    Allows adjusting margins, templates, DPI, and calibration.
    """
    from core.services.permissions import PlanPermissionService

    if not PlanPermissionService.check(request.shop, "print_tags"):
        from django.contrib import messages
        from django.shortcuts import redirect

        messages.error(request, "Your trial or subscription has expired. Please upgrade to unlock this feature.")
        return redirect("dashboard:home")

    ids_str = request.GET.get("ids", "")
    item_ids = [int(x) for x in ids_str.split(",") if x.isdigit()]

    items = JewelleryItem.objects.filter(shop=request.shop, id__in=item_ids)

    # Fetch active templates (either scoped to shop or global defaults)
    templates = LabelTemplate.objects.filter(Q(shop=request.shop) | Q(shop__isnull=True), is_active=True).order_by(
        "name", "-version"
    )

    # Group templates by slug and take the highest version
    grouped_templates = {}
    for t in templates:
        if t.slug not in grouped_templates:
            grouped_templates[t.slug] = t

    # Log print event
    if items.exists():
        first_item = items.first()
        event_type = "PRINT_LABEL" if items.count() == 1 else "PRINT_BULK"
        BarcodeEvent.objects.create(
            shop=request.shop,
            user=request.user if request.user.is_authenticated else None,
            event_type=event_type,
            sku_snapshot=first_item.design_code,
            metadata={
                "item_ids": [item.id for item in items],
                "count": items.count(),
                "skus": [item.design_code for item in items],
            },
        )

    context = {
        "items": items,
        "templates": grouped_templates.values(),
        "default_template": next((t for t in grouped_templates.values() if t.is_default), None)
        or next(iter(grouped_templates.values()), None),
    }
    return render(request, "inventory/print_tag.html", context)


@login_required
def item_lookup_api(request):
    """
    Lookup endpoint that searches by SKU (design_code), UUID, or product name.
    Strict tenant isolation: filters strictly by current shop context.
    """
    code = request.GET.get("code", "").strip()
    if not code:
        return JsonResponse(
            {"success": False, "error_code": "EMPTY_CODE", "message": "No lookup code provided."}, status=400
        )

    shop = request.shop
    item = None

    # Try parsing code as UUID first
    try:
        parsed_uuid = uuid.UUID(code)
        item = JewelleryItem.objects.filter(shop=shop, uuid=parsed_uuid).first()
    except ValueError:
        pass

    # Search by SKU (design_code)
    if not item:
        item = JewelleryItem.objects.filter(shop=shop, design_code=code).first()

    # Search by exact name as fallback
    if not item:
        item = JewelleryItem.objects.filter(shop=shop, item_name__iexact=code).first()

    if not item:
        # Log failed scan
        BarcodeEvent.objects.create(
            shop=shop,
            user=request.user if request.user.is_authenticated else None,
            event_type="SCAN_FAILED",
            sku_snapshot=code[:100],
            metadata={"reason": "NOT_FOUND"},
        )
        return JsonResponse(
            {"success": False, "error_code": "NOT_FOUND", "message": f"Item with code '{code}' not found."}, status=404
        )

    # Check if stock exists
    if item.stock_quantity <= 0:
        # Log failed scan due to out of stock
        BarcodeEvent.objects.create(
            shop=shop,
            user=request.user if request.user.is_authenticated else None,
            event_type="SCAN_FAILED",
            sku_snapshot=item.design_code,
            metadata={"item_id": item.id, "item_name": item.item_name, "reason": "OUT_OF_STOCK"},
        )
        return JsonResponse(
            {
                "success": False,
                "error_code": "OUT_OF_STOCK",
                "message": f"Item '{item.item_name}' ({item.design_code}) is out of stock.",
                "id": item.id,
                "sku": item.design_code,
                "name": item.item_name,
                "stock": item.stock_quantity,
            },
            status=200,
        )

    # Return success payload and log success scan
    current_price = item.get_current_price()
    BarcodeEvent.objects.create(
        shop=shop,
        user=request.user if request.user.is_authenticated else None,
        event_type="SCAN_SUCCESS",
        sku_snapshot=item.design_code,
        metadata={"item_id": item.id, "item_name": item.item_name, "price": float(current_price)},
    )
    return JsonResponse(
        {
            "success": True,
            "id": item.id,
            "sku": item.design_code,
            "uuid": str(item.uuid),
            "name": item.item_name,
            "weight": float(item.weight_in_grams),
            "stock": item.stock_quantity,
            "price": float(current_price),
            "metal": item.get_metal_type_display(),
            "image": item.image.url if item.image else "",
        }
    )


from django.core.paginator import Paginator


@login_required
def barcode_events_view(request):
    """
    Renders scanner and print audit log events scoped strictly by tenant.
    """
    events = BarcodeEvent.objects.filter(shop=request.shop).order_by("-created_at")

    # Filter by event type
    event_type = request.GET.get("event_type", "").strip()
    if event_type:
        events = events.filter(event_type=event_type)

    # Filter by SKU
    sku = request.GET.get("sku", "").strip()
    if sku:
        events = events.filter(sku_snapshot__icontains=sku)

    paginator = Paginator(events, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "event_types": BarcodeEvent.EVENT_TYPES,
        "selected_event_type": event_type,
        "selected_sku": sku,
    }
    return render(request, "barcodes/audit_logs.html", context)
