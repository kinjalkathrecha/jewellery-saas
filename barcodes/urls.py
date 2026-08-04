from django.urls import path

from core.decorators import redis_rate_limit

from . import views

app_name = "barcodes"

urlpatterns = [
    path(
        "lookup/",
        redis_rate_limit("barcode_api", 100, 60, limit_by="shop")(views.item_lookup_api),
        name="item_lookup_api",
    ),
    path("print-tags/", views.print_tags_view, name="print_tags"),
    path("events/", views.barcode_events_view, name="barcode_events"),
]
