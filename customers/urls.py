from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Customer List and CRUD
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    
    # Notes
    path('<int:pk>/add-note/', views.CustomerNoteCreateView.as_view(), name='customer_add_note'),
    
    # Excel Import/Export
    path('import/', views.CustomerImportView.as_view(), name='customer_import'),
    path('export/', views.customer_export_excel, name='customer_export'),
    path('template/', views.customer_download_template, name='customer_template'),
    
    # Customer Segments
    path('segments/', views.CustomerSegmentListView.as_view(), name='segment_list'),
    path('segments/create/', views.CustomerSegmentCreateView.as_view(), name='segment_create'),
    path('segments/<int:pk>/edit/', views.CustomerSegmentUpdateView.as_view(), name='segment_update'),
]
