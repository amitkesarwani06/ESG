"""
Normalization model: NormalizedRecord.

Why a separate table instead of columns on RawRecord?

1. Separation of concerns: RawRecord is immutable. NormalizedRecord
   can be re-generated if our normalization logic changes.
   This gives us an upgrade path without touching the audit trail.

2. Not all rows will have successful normalization — error rows
   (SUSPICIOUS status) may have no normalized counterpart at all,
   or a partial one. NULL-ing out fields on RawRecord would be confusing.

3. It makes the data model self-documenting: if you see a NormalizedRecord,
   you know we have a clean, processed interpretation.

quantity_unit is always stored in canonical SI units:
  - Liquid fuels: liters (L)
  - Electricity: kWh (kWh is the practical standard for electricity)
  - Distance: km

co2e_kg: The primary output field. Stored as a computed value after
normalization so the API can return it without re-running calculations.
"""
import uuid
from django.db import models
from ingestion.models import RawRecord


class NormalizedRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # One-to-one: each raw record has at most one normalized version
    raw_record = models.OneToOneField(
        RawRecord,
        on_delete=models.CASCADE,
        related_name="normalized"
    )
    source_type_code = models.CharField(max_length=50, db_index=True)

    # --- Common normalized fields ---
    record_date = models.DateField(null=True, blank=True)
    facility_code = models.CharField(max_length=100, blank=True)

    # Normalized quantity — always in canonical unit for this source type
    quantity_value = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    quantity_unit = models.CharField(max_length=20, blank=True)

    # GHG output — the number that goes to auditors
    co2e_kg = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        help_text="CO2 equivalent in kg. Computed from emission factors at normalization time."
    )

    # --- SAP Fuel fields ---
    fuel_type = models.CharField(max_length=100, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    material_code = models.CharField(max_length=100, blank=True)

    # --- Utility Electricity fields ---
    meter_id = models.CharField(max_length=100, blank=True)
    consumption_kwh = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    tariff = models.CharField(max_length=100, blank=True)
    billing_start = models.DateField(null=True, blank=True)
    billing_end = models.DateField(null=True, blank=True)

    # --- Corporate Travel fields ---
    employee_id = models.CharField(max_length=100, blank=True)
    trip_type = models.CharField(max_length=50, blank=True)  # flight|hotel|ground
    departure_airport = models.CharField(max_length=3, blank=True)  # IATA code
    arrival_airport = models.CharField(max_length=3, blank=True)    # IATA code
    distance_km = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    cabin_class = models.CharField(max_length=50, blank=True)
    expense_amount_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    normalized_at = models.DateTimeField(auto_now_add=True)
    # Human-readable log of what transformations were applied
    normalization_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Normalized({self.raw_record_id}) — {self.co2e_kg} kg CO2e"

    class Meta:
        ordering = ["-normalized_at"]
