"""
Ingestion models: RawRecord.

The raw record is the immutable source of truth.
We store the entire CSV row as JSONB rather than trying to define
a fixed schema for each source type. Reasons:

1. SAP exports have ~200 possible column names depending on the
   transaction type, plant, and SAP version. Modeling all of them
   would be premature and brittle.

2. The raw_data field acts as a "snapshot" — even if our normalization
   logic has a bug, we can always re-process from raw.

3. JSONB is indexed and queryable in PostgreSQL, so we don't lose
   query flexibility by using it.

The status field is intentionally denormalized here (the canonical
state lives in approval_actions). We keep it for fast dashboard queries
without joining to the audit table.
"""
import uuid
from django.db import models
from core.models import UploadBatch


class RawRecord(models.Model):
    """
    One row per CSV row in the uploaded file.

    raw_data: the original key-value pairs from the CSV row,
              stored exactly as parsed (messy column names, raw strings).
    row_index: the 0-based row number in the source file, for tracing
               back to the original spreadsheet.
    status: denormalized view of the review state for query efficiency.
    """
    class RecordStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        SUSPICIOUS = "suspicious", "Suspicious"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        UploadBatch,
        on_delete=models.CASCADE,
        related_name="raw_records"
    )
    row_index = models.IntegerField(
        help_text="0-based row number in the source CSV file"
    )
    raw_data = models.JSONField(
        help_text="Original CSV row stored as-is. Never modified after insert."
    )
    ingested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=RecordStatus.choices,
        default=RecordStatus.PENDING,
        db_index=True
    )

    def __str__(self):
        return f"Row {self.row_index} of {self.batch.filename} [{self.status}]"

    class Meta:
        ordering = ["batch", "row_index"]
        # Prevent duplicate row ingestion from the same batch
        unique_together = [("batch", "row_index")]
