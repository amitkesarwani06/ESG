"""
Main ingestion pipeline service.

This is the orchestrator that ties together:
  parsing → raw record storage → validation → normalization → status update

Called synchronously from the upload API view.

Why synchronous (not Celery async)?
- CSV files in this context are < 10MB, typically < 5,000 rows
- Synchronous processing keeps the code simple and debuggable
- The API response can include immediate stats (row count, error count)
- Async processing would require polling for status, adding frontend complexity

If we needed to handle 100k+ row files, we'd move to Celery.
That's documented as a known scaling tradeoff.
"""
from django.db import transaction
from ingestion.models import RawRecord
from validation.models import ValidationIssue
from normalization.models import NormalizedRecord
from normalization.services.normalizer import run_normalization
from review.models import AuditLog
from .sap_parser import parse_sap_fuel_csv
from .utility_parser import parse_utility_electricity_csv
from .travel_parser import parse_corporate_travel_csv
from validation.services.sap_validator import SAPFuelValidator
from validation.services.utility_validator import UtilityElectricityValidator
from validation.services.travel_validator import TravelValidator

# Registry: source type code → (parser_fn, validator_class)
SOURCE_REGISTRY = {
    "sap_fuel": (parse_sap_fuel_csv, SAPFuelValidator),
    "utility_elec": (parse_utility_electricity_csv, UtilityElectricityValidator),
    "corporate_travel": (parse_corporate_travel_csv, TravelValidator),
}


def ingest_batch(batch, file_content: bytes) -> dict:
    """
    Process a single uploaded CSV file through the full ingestion pipeline.

    Steps:
    1. Parse CSV rows using source-specific parser
    2. For each row: create RawRecord (immutable)
    3. Run validator → create ValidationIssues
    4. Run normalizer → create NormalizedRecord
    5. Set record status based on validation severity
    6. Update batch statistics

    Returns a stats dict with counts for dashboard display.

    All DB writes are in a single transaction — if parsing fails midway,
    no partial data is committed.
    """
    source_code = batch.source_type.code
    if source_code not in SOURCE_REGISTRY:
        raise ValueError(f"No parser registered for source type: '{source_code}'")

    parser_fn, validator_class = SOURCE_REGISTRY[source_code]

    # Instantiate fresh validator for each batch (some validators are stateful,
    # e.g., UtilityElectricityValidator tracks billing periods for overlap detection)
    validator = validator_class()

    stats = {
        "total_rows": 0,
        "pending_rows": 0,
        "suspicious_rows": 0,
        "normalization_errors": 0,
    }

    with transaction.atomic():
        try:
            rows = list(parser_fn(file_content))
        except Exception as e:
            batch.status = "failed"
            batch.error_message = f"CSV parsing failed: {str(e)}"
            batch.save(update_fields=["status", "error_message"])
            raise

        raw_records_to_create = []
        for idx, row in enumerate(rows):
            raw_records_to_create.append(
                RawRecord(
                    batch=batch,
                    row_index=idx,
                    raw_data=row,
                    status=RawRecord.RecordStatus.PENDING,
                )
            )

        # Bulk create all raw records in one query
        # ignore_conflicts=True: gracefully handles re-upload of same file
        # Note: bulk_create with ignore_conflicts returns only the created objects
        # on PostgreSQL; on SQLite it may return all attempted objects.
        # We re-query to get the actual created records with their PKs.
        RawRecord.objects.bulk_create(
            raw_records_to_create,
            ignore_conflicts=True
        )
        created_records = list(
            RawRecord.objects.filter(batch=batch).order_by("row_index")
        )
        stats["total_rows"] = len(created_records)

        # Validate + normalize each record
        issues_to_create = []
        normalized_to_create = []
        records_to_update = []

        for raw_record in created_records:
            # Validation
            validation_result = validator.validate_row(raw_record.raw_data)

            for issue in validation_result.issues:
                issues_to_create.append(
                    ValidationIssue(
                        raw_record=raw_record,
                        issue_code=issue.code,
                        severity=issue.severity,
                        field_name=issue.field_name,
                        message=issue.message,
                    )
                )

            # Update status based on validation
            if validation_result.has_errors:
                raw_record.status = RawRecord.RecordStatus.SUSPICIOUS
                stats["suspicious_rows"] += 1
            else:
                raw_record.status = RawRecord.RecordStatus.PENDING
                stats["pending_rows"] += 1
            records_to_update.append(raw_record)

            # Normalization (even for suspicious rows — partial normalization is useful)
            try:
                normalized = run_normalization(raw_record)
                normalized_to_create.append(normalized)
            except Exception as e:
                stats["normalization_errors"] += 1
                # Log but don't fail — normalization errors don't block ingestion
                issues_to_create.append(
                    ValidationIssue(
                        raw_record=raw_record,
                        issue_code="NORMALIZATION_ERROR",
                        severity="error",
                        field_name="",
                        message=f"Normalization failed: {str(e)}",
                    )
                )

        # Bulk write all changes
        RawRecord.objects.bulk_update(records_to_update, ["status"])
        ValidationIssue.objects.bulk_create(issues_to_create)
        # NormalizedRecord has a OneToOne constraint with RawRecord,
        # so ignore_conflicts=True safely handles re-processing the same batch.
        NormalizedRecord.objects.bulk_create(
            normalized_to_create,
            ignore_conflicts=True
        )

        # Update batch status
        batch.status = "completed"
        batch.row_count = stats["total_rows"]
        batch.save(update_fields=["status", "row_count"])

        # Audit log: batch ingestion completed
        AuditLog.objects.create(
            entity_type="upload_batch",
            entity_id=batch.id,
            action="batch_ingested",
            new_value=stats,
            actor="system",
        )

    return stats
