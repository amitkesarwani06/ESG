from django.contrib import admin
from .models import ApprovalAction, AuditLog


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ["id", "raw_record", "action", "analyst_name", "note", "acted_at"]
    list_filter = ["action", "acted_at"]
    search_fields = ["analyst_name", "note"]
    readonly_fields = ["id", "raw_record", "action", "analyst_name", "note", "acted_at"]
    ordering = ["-acted_at"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "id", "entity_type", "entity_id", "action", "actor", "occurred_at"
    ]
    list_filter = ["entity_type", "action", "actor"]
    search_fields = ["entity_type", "action", "actor"]
    readonly_fields = [
        "id", "entity_type", "entity_id", "action",
        "old_value", "new_value", "actor", "occurred_at"
    ]
    ordering = ["-occurred_at"]
