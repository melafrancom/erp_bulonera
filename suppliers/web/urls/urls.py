"""
URLs web para la app Suppliers.
"""
from django.urls import path
from suppliers.web.views import views

app_name = 'suppliers_web'

urlpatterns = [
    path('', views.supplier_list, name='supplier_list'),
    path('<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('create/', views.supplier_create, name='supplier_create'),
    path('<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('import/', views.supplier_import, name='supplier_import'),
    path('import/template/', views.supplier_download_template, name='supplier_download_template'),
]
