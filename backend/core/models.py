"""
Core models: Client, SourceType, UploadBatch.

These are the top-level organizational entities.

Design rationale:
- Client: multi-tenancy from day one. Even if we only have one client in the
  prototype, adding client_id to every batch keeps the schema honest and makes
  future multi-tenancy a DB query change, not a schema migration.

- SourceType: stored as a DB table rather than an enum so that the label and
  scope (1/2/3) are visible to analysts without code inspection.

- UploadBatch: one row per uploaded file. This is the unit of work — every
  raw record links back to a batch, giving us file-level provenance.
"""
import uuid
from django.db import models


class Client(models.Model):
    """
    Represents an enterprise client whose data we're ingesting.
    Using slug for URL-safe client identification in API paths.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class SourceType(models.Model):
    """
    Describes the type of data source.

    scope follows GHG Protocol categorization:
      1 = Direct emissions (e.g., fuel combustion)
      2 = Indirect from purchased energy (e.g., electricity)
      3 = Value chain emissions (e.g., business travel)

    We store the scope here so the API can expose it without
    the frontend needing to hard-code this business rule.
    """
    SCOPE_CHOICES = [(1, "Scope 1"), (2, "Scope 2"), (3, "Scope 3")]
    SOURCE_CODES = [
        ("sap_fuel", "SAP Fuel & Procurement"),
        ("utility_elec", "Utility Electricity"),
        ("corporate_travel", "Corporate Travel"),
    ]

    code = models.CharField(max_length=50, unique=True, choices=SOURCE_CODES)
    label = models.CharField(max_length=100)
    scope = models.SmallIntegerField(choices=SCOPE_CHOICES)

    def __str__(self):
        return f"{self.label} (Scope {self.scope})"

    class Meta:
        ordering = ["scope", "code"]


class UploadBatch(models.Model):
    """
    One row per CSV file uploaded.

    Why track batches separately from records?
    - Gives analysts a file-level view ("what did we receive on Tuesday?")
    - Allows batch-level locking (lock all approved records in a batch at once)
    - Preserves original filename for traceability back to the source system export

    status transitions:
      processing → completed (normal)
      processing → failed    (parse error, e.g., corrupted file)
    """
    class BatchStatus(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="batches"
    )
    source_type = models.ForeignKey(
        SourceType,
        on_delete=models.PROTECT,
        related_name="batches"
    )
    filename = models.CharField(max_length=500)
    uploaded_by = models.CharField(
        max_length=255,
        help_text="Analyst name or email. Not linked to auth user in this prototype."
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.PROCESSING
    )
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.filename} ({self.uploaded_at.date()})"

    class Meta:
        ordering = ["-uploaded_at"]
