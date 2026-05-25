"""
Review models: ApprovalAction, AuditLog.

ApprovalAction: append-only table of analyst decisions.
  - We never update or delete rows. Each decision is a new row.
  - This gives us a full decision history, not just the latest state.
  - The "current" status is on RawRecord.status (denormalized cache).

AuditLog: system-generated event log.
  - Records every state change to any entity.
  - old_value / new_value as JSONB captures the before/after snapshot.
  - Separate from ApprovalAction because the audit log also covers
    system-generated events (batch uploaded, normalization run) not just
    human approvals.
"""
import uuid
from django.db import models
from ingestion.models import RawRecord
from core.models import UploadBatch


class ApprovalAction(models.Model):
    """
    Immutable record of an analyst decision.

    Note: action='reject' is a soft flag — it means "do not include in
    audit export" but does not delete the raw record. This preserves
    the ingestion history.
    """
    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        FLAG = "flag", "Flag for Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_record = models.ForeignKey(
        RawRecord,
        on_delete=models.PROTECT,  # PROTECT: never silently delete audit history
        related_name="approval_actions"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    analyst_name = models.CharField(
        max_length=255,
        help_text="Analyst who made this decision. Plain string in prototype."
    )
    note = models.TextField(blank=True)
    acted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.analyst_name} on {self.acted_at.date()}"

    class Meta:
        ordering = ["-acted_at"]


class AuditLog(models.Model):
    """
    System-generated event log for all state changes.

    entity_type + entity_id form a polymorphic reference rather than
    separate FKs. This avoids a JOIN-heavy schema while keeping the
    audit log centralized and queryable by entity.

    In a production system, we'd also log IP address and user agent.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="e.g., 'raw_record', 'upload_batch'"
    )
    entity_id = models.UUIDField(db_index=True)
    action = models.CharField(
        max_length=100,
        help_text="e.g., 'status_changed', 'batch_uploaded', 'record_locked'"
    )
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    actor = models.CharField(
        max_length=255,
        blank=True,
        help_text="Analyst name or 'system' for automated events"
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.entity_type}:{self.entity_id}] {self.action} by {self.actor}"

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
        ]
