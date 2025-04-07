"""
URL configuration for testing the Django Audit Logger package.
"""
from django.contrib import admin
from django.urls import path
from .views import test_view, test_api_view, test_error_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', test_view, name='test_view'),
    path('api/test/', test_api_view, name='test_api_view'),
    path('error/', test_error_view, name='test_error_view'),
]
