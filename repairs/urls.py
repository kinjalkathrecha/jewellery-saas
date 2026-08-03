from django.urls import path

from . import views

app_name = 'repairs'

urlpatterns = [
    path('', views.RepairListView.as_view(), name='repair_list'),
    path('new/', views.RepairCreateView.as_view(), name='repair_add'),
    path('<int:pk>/', views.RepairDetailView.as_view(), name='repair_detail'),
    path('<int:pk>/edit/', views.RepairUpdateView.as_view(), name='repair_edit'),
    path('<int:pk>/delete/', views.RepairDeleteView.as_view(), name='repair_delete'),
    path('<int:pk>/status-update/', views.RepairStatusUpdateView.as_view(), name='status_update'),
    path('<int:pk>/pdf/', views.RepairPDFView.as_view(), name='repair_pdf'),
]
