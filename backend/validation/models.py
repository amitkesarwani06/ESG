"""
Validation model: ValidationIssue.

Each issue is a machine-generated flag on a raw record.
Multiple issues can exist per record (e.g., both missing field AND invalid date).

Design decisions:
- issue_code is a string constant (not an integer FK to an issue_types table)
  because codes need to be readable in logs and API responses without a join.
- severity 'error' vs 'warning':
    error   → row is marked SUSPICIOUS (blocks auto-approval)
    warning → row stays PENDING (analyst can approve despite the warning)
- field_name: pinpoints which column caused the issue. Crucial for analyst UX.
"""
import uuid
from django.db import models
from ingestion.models import RawRecord


class ValidationIssue(models.Model):
    class Severity(models.TextChoices):
        ERROR = "error", "Error"
        WARNING = "warning", "Warning"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_record = models.ForeignKey(
        RawRecord,
        on_delete=models.CASCADE,
        related_name="issues"
    )
    # Self-documenting string codes — see validation/services/issue_codes.py
    issue_code = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        db_index=True
    )
    # Which field in the raw CSV row triggered this issue
    field_name = models.CharField(max_length=100, blank=True)
    # Human-readable description shown to analysts
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity.upper()}] {self.issue_code} on record {self.raw_record_id}"

    class Meta:
        ordering = ["severity", "issue_code"]
