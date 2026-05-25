"""
Main normalizer service — orchestrates normalization for each source type.

The normalizer takes a validated raw_record and produces a NormalizedRecord.
It is called AFTER validation, so it can assume the row has passed basic
structural checks (though it handles None/missing gracefully anyway).

The normalization_notes field accumulates a log of every transformation
applied — this is the paper trail for auditors asking "why does this row
show 3785.41 L when the source said 1000 GAL?"
"""
from decimal import Decimal
from normalization.models import NormalizedRecord
from normalization.services.date_normalizer import DateNormalizer
from normalization.services.unit_converter import UnitConverter
from emissions.factors import SAP_FUEL_TYPE_ALIASES
from emissions.calculator import (
    calculate_fuel_co2e,
    calculate_electricity_co2e,
    calculate_flight_co2e,
    calculate_hotel_co2e,
    calculate_ground_transport_co2e,
)

date_normalizer = DateNormalizer()
unit_converter = UnitConverter()

# Common IATA code aliases — city names or alternate codes that appear
# in Concur/Navan exports when travelers enter free text
IATA_ALIASES = {
    "MUMBAI": "BOM", "BOMBAY": "BOM",
    "DELHI": "DEL", "NEW DELHI": "DEL",
    "BANGALORE": "BLR", "BENGALURU": "BLR",
    "LONDON": "LHR",  # Assumes Heathrow — ambiguous, flag in production
    "NEW YORK": "JFK",
    "NYC": "JFK",
    "FRANKFURT": "FRA",
    "DUBAI": "DXB",
    "SINGAPORE": "SIN",
    "CHICAGO": "ORD",
    "LOS ANGELES": "LAX",
    "LA": "LAX",
}


def normalize_sap_fuel(raw_record) -> NormalizedRecord:
    """
    Normalize a SAP fuel/procurement raw record.

    The raw row may have:
    - German column names (already mapped by SAP parser)
    - Comma as decimal separator
    - Various unit codes
    - Multiple date formats
    """
    row = raw_record.raw_data
    notes = []

    # --- Facility code: strip SAP leading zeros ---
    facility = str(row.get("plant_code", "")).strip()
    # SAP pads plant codes to 4 digits: "0001" → store as-is for lookups
    # (removing leading zeros would break cross-reference with SAP master data)

    # --- Date ---
    date_str = str(row.get("transaction_date", "")).strip()
    record_date, date_note = date_normalizer.normalize(date_str, prefer_us_format=False)
    notes.append(date_note)

    # --- Quantity: handle European decimal comma ---
    qty_str = str(row.get("quantity", "0")).strip().replace(",", ".")
    try:
        quantity = float(qty_str)
    except ValueError:
        quantity = None
        notes.append(f"Could not parse quantity: '{qty_str}'")

    # --- Unit conversion ---
    raw_unit = str(row.get("unit", "")).strip().upper()
    if quantity is not None and raw_unit:
        converted_qty, canonical_unit, unit_note = unit_converter.convert(quantity, raw_unit)
        notes.append(unit_note)
    else:
        converted_qty = quantity
        canonical_unit = raw_unit
        notes.append("No unit conversion applied (missing quantity or unit)")

    # --- Fuel type normalization ---
    raw_fuel = str(row.get("fuel_type", "")).strip().lower()
    canonical_fuel = SAP_FUEL_TYPE_ALIASES.get(raw_fuel, raw_fuel)
    if canonical_fuel != raw_fuel:
        notes.append(f"Fuel type '{raw_fuel}' → '{canonical_fuel}'")

    # --- CO2e calculation ---
    co2e_kg = None
    if converted_qty is not None and canonical_unit:
        co2e, co2e_note = calculate_fuel_co2e(canonical_fuel, converted_qty, canonical_unit)
        co2e_kg = Decimal(str(co2e)) if co2e is not None else None
        notes.append(co2e_note)

    return NormalizedRecord(
        raw_record=raw_record,
        source_type_code="sap_fuel",
        record_date=record_date,
        facility_code=facility,
        quantity_value=Decimal(str(converted_qty)) if converted_qty is not None else None,
        quantity_unit=canonical_unit,
        co2e_kg=co2e_kg,
        fuel_type=canonical_fuel,
        vendor=str(row.get("vendor", "")).strip(),
        material_code=str(row.get("material_code", "")).strip(),
        normalization_notes="\n".join(notes),
    )


def normalize_utility_electricity(raw_record) -> NormalizedRecord:
    """Normalize a utility electricity billing row."""
    row = raw_record.raw_data
    notes = []

    facility = str(row.get("facility", "")).strip()
    meter_id = str(row.get("meter_id", "")).strip()

    # --- Billing dates ---
    billing_start_str = str(row.get("billing_start", "")).strip()
    billing_end_str = str(row.get("billing_end", "")).strip()
    billing_start, start_note = date_normalizer.normalize(billing_start_str)
    billing_end, end_note = date_normalizer.normalize(billing_end_str)
    notes.extend([start_note, end_note])

    # Use billing_end as the record_date (conventional for billing data)
    record_date = billing_end

    # --- Consumption ---
    kwh_str = str(row.get("consumption_kwh", "0")).strip().replace(",", "")
    try:
        kwh = float(kwh_str)
    except ValueError:
        kwh = None
        notes.append(f"Could not parse consumption_kwh: '{kwh_str}'")

    # --- CO2e (location-based, India grid by default) ---
    # In production: facility country code would be on the Facility master record
    co2e_kg = None
    if kwh is not None:
        co2e, co2e_note = calculate_electricity_co2e(kwh, country_code="IN")
        co2e_kg = Decimal(str(co2e)) if co2e is not None else None
        notes.append(co2e_note)

    return NormalizedRecord(
        raw_record=raw_record,
        source_type_code="utility_elec",
        record_date=record_date,
        facility_code=facility,
        quantity_value=Decimal(str(kwh)) if kwh is not None else None,
        quantity_unit="kWh",
        co2e_kg=co2e_kg,
        meter_id=meter_id,
        consumption_kwh=Decimal(str(kwh)) if kwh is not None else None,
        tariff=str(row.get("tariff", "")).strip(),
        billing_start=billing_start,
        billing_end=billing_end,
        normalization_notes="\n".join(notes),
    )


def normalize_corporate_travel(raw_record) -> NormalizedRecord:
    """Normalize a corporate travel record from Concur/Navan export."""
    row = raw_record.raw_data
    notes = []

    trip_type = str(row.get("trip_type", "")).strip().lower()
    employee_id = str(row.get("employee_id", "")).strip()

    # --- Date ---
    date_str = str(row.get("trip_date", "")).strip()
    record_date, date_note = date_normalizer.normalize(date_str, prefer_us_format=True)
    notes.append(date_note)

    # --- Airport codes: normalize to IATA ---
    def normalize_airport(code: str) -> str:
        code = code.strip().upper()
        # Check alias table (city names → IATA)
        if code in IATA_ALIASES:
            notes.append(f"Airport name '{code}' → IATA code '{IATA_ALIASES[code]}'")
            return IATA_ALIASES[code]
        return code

    dep_airport = normalize_airport(str(row.get("departure_airport", "")))
    arr_airport = normalize_airport(str(row.get("arrival_airport", "")))

    # --- Distance: handle miles → km ---
    dist_str = str(row.get("distance", "") or row.get("distance_km", "")).strip()
    distance_km = None
    if dist_str:
        try:
            raw_dist = float(dist_str.replace(",", ""))
            dist_unit = str(row.get("distance_unit", "km")).strip().lower()
            if dist_unit in ("mi", "miles", "mile"):
                distance_km = raw_dist * 1.60934
                notes.append(f"Distance {raw_dist} miles → {distance_km:.2f} km")
            else:
                distance_km = raw_dist
                notes.append(f"Distance: {distance_km} km (already in km)")
        except ValueError:
            notes.append(f"Could not parse distance: '{dist_str}'")

    # --- Cabin class normalization ---
    raw_cabin = str(row.get("cabin_class", "") or row.get("class_of_service", "")).strip().lower()
    # Map Concur's verbose class names to canonical
    cabin_map = {
        "coach": "economy", "y": "economy", "economy class": "economy",
        "business class": "business", "c": "business",
        "first class": "first", "f": "first",
        "premium economy": "premium_economy", "w": "premium_economy",
    }
    cabin_class = cabin_map.get(raw_cabin, raw_cabin or "economy")
    if raw_cabin and raw_cabin != cabin_class:
        notes.append(f"Cabin class '{raw_cabin}' → '{cabin_class}'")

    # --- Expense amount: normalize to USD ---
    expense_str = str(row.get("expense_amount", "0")).strip().replace(",", "")
    expense_currency = str(row.get("expense_currency", "USD")).strip().upper()
    try:
        expense_amount = float(expense_str)
        if expense_currency != "USD":
            notes.append(
                f"Expense {expense_amount} {expense_currency} — currency conversion "
                f"not applied in prototype. Stored as original amount."
            )
    except ValueError:
        expense_amount = None

    # --- CO2e calculation ---
    co2e_kg = None
    if trip_type == "flight" and distance_km is not None:
        co2e, co2e_note = calculate_flight_co2e(distance_km, cabin_class)
        co2e_kg = Decimal(str(co2e)) if co2e else None
        notes.append(co2e_note)
    elif trip_type == "hotel":
        nights_str = str(row.get("nights", "1")).strip()
        try:
            nights = int(nights_str)
            co2e, co2e_note = calculate_hotel_co2e(nights)
            co2e_kg = Decimal(str(co2e)) if co2e else None
            notes.append(co2e_note)
        except ValueError:
            notes.append(f"Could not parse nights: '{nights_str}'")
    elif trip_type in ("ground", "taxi", "car_rental", "rail"):
        if distance_km is not None:
            co2e, co2e_note = calculate_ground_transport_co2e(distance_km, trip_type)
            co2e_kg = Decimal(str(co2e)) if co2e else None
            notes.append(co2e_note)

    return NormalizedRecord(
        raw_record=raw_record,
        source_type_code="corporate_travel",
        record_date=record_date,
        facility_code="",  # Not applicable for travel
        quantity_value=Decimal(str(distance_km)) if distance_km else None,
        quantity_unit="km",
        co2e_kg=co2e_kg,
        employee_id=employee_id,
        trip_type=trip_type,
        departure_airport=dep_airport[:3] if dep_airport else "",
        arrival_airport=arr_airport[:3] if arr_airport else "",
        distance_km=Decimal(str(distance_km)) if distance_km else None,
        cabin_class=cabin_class,
        expense_amount_usd=Decimal(str(expense_amount)) if expense_amount else None,
        normalization_notes="\n".join(filter(None, notes)),
    )


# Registry mapping source type codes to their normalizer functions
NORMALIZERS = {
    "sap_fuel": normalize_sap_fuel,
    "utility_elec": normalize_utility_electricity,
    "corporate_travel": normalize_corporate_travel,
}


def run_normalization(raw_record) -> NormalizedRecord:
    """
    Dispatch to the correct normalizer for a raw record's source type.
    Creates and returns (but does not save) a NormalizedRecord.
    """
    source_code = raw_record.batch.source_type.code
    normalizer_fn = NORMALIZERS.get(source_code)
    if normalizer_fn is None:
        raise ValueError(f"No normalizer registered for source type: '{source_code}'")
    return normalizer_fn(raw_record)
