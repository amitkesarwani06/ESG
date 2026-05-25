import os
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from core.models import Client, SourceType, UploadBatch
from ingestion.models import RawRecord
from normalization.models import NormalizedRecord
from validation.models import ValidationIssue
from review.models import ApprovalAction, AuditLog
from ingestion.services.pipeline import ingest_batch

def test_pipeline():
    print("=== STARTING PIPELINE INTEGRATION TESTS ===")
    
    # 1. Clear database to start clean
    print("Clearing existing data...")
    ApprovalAction.objects.all().delete()
    AuditLog.objects.all().delete()
    ValidationIssue.objects.all().delete()
    NormalizedRecord.objects.all().delete()
    RawRecord.objects.all().delete()
    UploadBatch.objects.all().delete()
    
    client, _ = Client.objects.get_or_create(
        name="Acme Corporation",
        slug="acme-corp"
    )
    
    sources = {
        "sap_fuel": "sample_data/sap_fuel_export.csv",
        "utility_elec": "sample_data/utility_electricity.csv",
        "corporate_travel": "sample_data/travel_concur_export.csv",
    }
    
    for code, file_path in sources.items():
        print(f"\n--- Testing Ingestion for {code} ({file_path}) ---")
        st = SourceType.objects.get(code=code)
        
        # Read the file
        full_path = os.path.join("..", file_path)
        with open(full_path, "rb") as f:
            content = f.read()
            
        # Create a batch
        batch = UploadBatch.objects.create(
            client=client,
            source_type=st,
            filename=os.path.basename(file_path),
            uploaded_by="system_test@breathe.esg",
            status="processing"
        )
        
        # Run ingestion
        try:
            stats = ingest_batch(batch, content)
            print(f"Ingestion successful! Stats: {stats}")
            
            # Verify batch status is completed
            batch.refresh_from_db()
            print(f"Batch status: {batch.status}, Row count: {batch.row_count}")
            
            # Print created records
            raws = RawRecord.objects.filter(batch=batch)
            print(f"Raw records created: {raws.count()}")
            
            normalizeds = NormalizedRecord.objects.filter(raw_record__batch=batch)
            print(f"Normalized records created: {normalizeds.count()}")
            
            issues = ValidationIssue.objects.filter(raw_record__batch=batch)
            print(f"Validation issues created: {issues.count()} (Errors: {issues.filter(severity='error').count()}, Warnings: {issues.filter(severity='warning').count()})")
            
            # Check a few normalized values
            for norm in normalizeds[:3]:
                co2e_str = f"{norm.co2e_kg:.2f}" if norm.co2e_kg is not None else "N/A"
                print(f"  Row {norm.raw_record.row_index}: Date={norm.record_date}, Facility={norm.facility_code}, Qty={norm.quantity_value} {norm.quantity_unit}, CO2e={co2e_str} kg")
                
        except Exception as e:
            print(f"INGESTION FAILED for {code}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()
