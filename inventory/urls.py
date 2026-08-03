from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="item_list"),
    path("rates/", views.MetalRatesView.as_view(), name="metal_rates"),
    path("add/", views.ItemCreateView.as_view(), name="item_add"),
    path("<int:pk>/edit/", views.ItemUpdateView.as_view(), name="item_edit"),
    path("<int:pk>/delete/", views.ItemDeleteView.as_view(), name="item_delete"),
]
