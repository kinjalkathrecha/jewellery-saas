from django.urls import path

from . import views

app_name = "barcodes"

urlpatterns = [
    path("lookup/", views.item_lookup_api, name="item_lookup_api"),
    path("print-tags/", views.print_tags_view, name="print_tags"),
    path("events/", views.barcode_events_view, name="barcode_events"),
]
