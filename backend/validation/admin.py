from django.contrib import admin
from .models import ValidationIssue


@admin.register(ValidationIssue)
class ValidationIssueAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "raw_record",
        "issue_code",
        "severity",
        "field_name",
        "message",
        "created_at",
    ]
    list_filter = ["severity", "issue_code"]
    search_fields = ["issue_code", "field_name", "message"]
    readonly_fields = ["id", "raw_record", "issue_code", "severity", "field_name", "message", "created_at"]
    ordering = ["-created_at"]
