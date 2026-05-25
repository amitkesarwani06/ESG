"""
Root URL configuration.

We prefix all API routes with /api/ to make it unambiguous
when the Django app also serves static files via whitenoise.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("ingestion.urls")),
    path("api/", include("review.urls")),
]
