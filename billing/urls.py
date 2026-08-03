from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice_list'),
    path('new/', views.InvoiceCreateView.as_view(), name='invoice_add'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('api/get-item-price/', views.get_item_price, name='api_get_item_price'),
    path('subscription/', views.billing_subscription_view, name='subscription_details'),
    path('subscription/upgrade/', views.upgrade_subscription_view, name='subscription_upgrade'),
]
