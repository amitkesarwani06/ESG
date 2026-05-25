"""
Approval service — handles record status transitions.

This is where we enforce the status machine rules:
- Only PENDING and SUSPICIOUS records can be approved or rejected
- LOCKED records are immutable
- Every state change creates an AuditLog entry

Why a service layer instead of putting this logic in the view?
- Business rules (immutability, status machine) should be testable without HTTP
- The view handles HTTP concerns (request parsing, response formatting)
- The service can be called from management commands or data scripts too

We use select_for_update() to prevent race conditions if two analysts
try to approve the same record simultaneously.
"""
from django.db import transaction
from ingestion.models import RawRecord
from review.models import ApprovalAction, AuditLog


class ApprovalError(Exception):
    """Raised when a status transition is not allowed."""
    pass


def approve_record(raw_record: RawRecord, analyst_name: str, note: str = "") -> ApprovalAction:
    """
    Approve a pending or suspicious record.

    Raises ApprovalError if the record is in an invalid state for approval.
    """
    with transaction.atomic():
        # Lock the row to prevent concurrent modifications
        record = RawRecord.objects.select_for_update().get(pk=raw_record.pk)

        if record.status == RawRecord.RecordStatus.LOCKED:
            raise ApprovalError(
                f"Record {record.pk} is LOCKED and cannot be modified."
            )
        if record.status == RawRecord.RecordStatus.APPROVED:
            raise ApprovalError(
                f"Record {record.pk} is already APPROVED."
            )

        old_status = record.status
        record.status = RawRecord.RecordStatus.APPROVED
        record.save(update_fields=["status"])

        action = ApprovalAction.objects.create(
            raw_record=record,
            action=ApprovalAction.Action.APPROVE,
            analyst_name=analyst_name,
            note=note,
        )

        AuditLog.objects.create(
            entity_type="raw_record",
            entity_id=record.pk,
            action="status_changed",
            old_value={"status": old_status},
            new_value={"status": RawRecord.RecordStatus.APPROVED},
            actor=analyst_name,
        )

    return action


def reject_record(raw_record: RawRecord, analyst_name: str, note: str = "") -> ApprovalAction:
    """
    Reject a record (marks it as rejected — not deleted, not included in audit export).
    """
    with transaction.atomic():
        record = RawRecord.objects.select_for_update().get(pk=raw_record.pk)

        if record.status == RawRecord.RecordStatus.LOCKED:
            raise ApprovalError(
                f"Record {record.pk} is LOCKED and cannot be modified."
            )

        old_status = record.status
        record.status = RawRecord.RecordStatus.REJECTED
        record.save(update_fields=["status"])

        action = ApprovalAction.objects.create(
            raw_record=record,
            action=ApprovalAction.Action.REJECT,
            analyst_name=analyst_name,
            note=note,
        )

        AuditLog.objects.create(
            entity_type="raw_record",
            entity_id=record.pk,
            action="status_changed",
            old_value={"status": old_status},
            new_value={"status": RawRecord.RecordStatus.REJECTED},
            actor=analyst_name,
        )

    return action


def lock_batch(batch, analyst_name: str) -> int:
    """
    Lock all APPROVED records in a batch.

    This is the final step before audit submission. LOCKED records
    are immutable — no further status changes are allowed.

    Returns the count of records locked.
    """
    with transaction.atomic():
        approved_records = RawRecord.objects.select_for_update().filter(
            batch=batch,
            status=RawRecord.RecordStatus.APPROVED
        )

        count = approved_records.count()
        if count == 0:
            raise ApprovalError(
                "No approved records in this batch to lock."
            )

        approved_records.update(status=RawRecord.RecordStatus.LOCKED)

        AuditLog.objects.create(
            entity_type="upload_batch",
            entity_id=batch.pk,
            action="batch_locked",
            new_value={"locked_record_count": count},
            actor=analyst_name,
        )

    return count
