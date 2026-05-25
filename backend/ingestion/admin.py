from django.contrib import admin
from .models import RawRecord


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id", "batch", "row_index", "status", "ingested_at"
    ]
    list_filter = ["status", "batch__source_type__code"]
    search_fields = ["batch__filename"]
    readonly_fields = ["id", "batch", "row_index", "raw_data", "status", "ingested_at"]
    ordering = ["batch", "row_index"]
