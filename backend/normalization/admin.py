from django.contrib import admin
from .models import NormalizedRecord


@admin.register(NormalizedRecord)
class NormalizedRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "source_type_code",
        "record_date",
        "facility_code",
        "quantity_value",
        "quantity_unit",
        "co2e_kg",
        "fuel_type",
        "trip_type",
        "normalized_at",
    ]
    list_filter = ["source_type_code", "record_date", "trip_type"]
    search_fields = ["facility_code", "fuel_type", "employee_id", "meter_id"]
    readonly_fields = [
        "id", "raw_record", "source_type_code", "record_date",
        "facility_code", "quantity_value", "quantity_unit", "co2e_kg",
        "fuel_type", "vendor", "material_code",
        "meter_id", "consumption_kwh", "tariff", "billing_start", "billing_end",
        "employee_id", "trip_type", "departure_airport", "arrival_airport",
        "distance_km", "cabin_class", "expense_amount_usd",
        "normalized_at", "normalization_notes",
    ]
    ordering = ["-normalized_at"]
