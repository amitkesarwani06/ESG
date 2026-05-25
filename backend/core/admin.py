from django.contrib import admin
from core.models import Client, SourceType, UploadBatch


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]


@admin.register(SourceType)
class SourceTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "scope"]


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ["filename", "client", "source_type", "uploaded_by", "uploaded_at", "status", "row_count"]
    list_filter = ["status", "source_type"]
    search_fields = ["filename", "uploaded_by"]
    readonly_fields = ["uploaded_at"]
