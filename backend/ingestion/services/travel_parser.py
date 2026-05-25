"""
Corporate Travel CSV parser.

Based on research into Concur Travel & Expense and Navan (formerly TripActions)
export formats.

Concur SAE (Standard Accounting Extract) format:
- Fixed column set, can be customized per company
- Expense types include: AIRFR (Airfare), HOTEL, CARRT (Car Rental), TRAIN
- Amounts in original expense currency + company currency
- Employee ID matches HR system (typically)
- Class of service: COACH, BUSINESS, FIRST, PREMIUM_ECONOMY
- Distance not always included — may need airport pair lookup

Navan CSV format:
- More flexible column naming
- Includes carbon emissions estimate (we ignore — we calculate our own)
- Better structured than Concur
- Booking date vs travel date (we use travel date)

We model our sample on Concur SAE as it's more widely deployed.
Reference: Concur Implementation Guide, SAE File Format Specification
"""
import csv
import io
import re
from typing import Iterator, Dict

COLUMN_ALIASES = {
    # Employee
    "employee_id": "employee_id",
    "employee id": "employee_id",
    "emp id": "employee_id",
    "user id": "employee_id",
    "traveler id": "employee_id",
    "staff id": "employee_id",

    # Trip type
    "trip_type": "trip_type",
    "expense type": "trip_type",
    "expense_type": "trip_type",
    "category": "trip_type",
    "travel type": "trip_type",
    "type": "trip_type",
    "segment type": "trip_type",

    # Airports
    "departure_airport": "departure_airport",
    "departure airport": "departure_airport",
    "origin": "departure_airport",
    "from": "departure_airport",
    "from airport": "departure_airport",
    "departure city": "departure_airport",

    "arrival_airport": "arrival_airport",
    "arrival airport": "arrival_airport",
    "destination": "arrival_airport",
    "to": "arrival_airport",
    "to airport": "arrival_airport",
    "arrival city": "arrival_airport",

    # Distance
    "distance_km": "distance_km",
    "distance": "distance",
    "miles": "distance",
    "km": "distance_km",
    "mileage": "distance",

    # Cabin class
    "cabin_class": "cabin_class",
    "cabin class": "cabin_class",
    "class of service": "cabin_class",
    "service class": "cabin_class",
    "fare class": "cabin_class",
    "travel class": "cabin_class",

    # Hotel
    "hotel_name": "facility",
    "hotel name": "facility",
    "property name": "facility",
    "nights": "nights",
    "number of nights": "nights",
    "hotel nights": "nights",

    # Expense amount
    "expense_amount": "expense_amount",
    "amount": "expense_amount",
    "total amount": "expense_amount",
    "approved amount": "expense_amount",
    "reimbursement amount": "expense_amount",

    "expense_currency": "expense_currency",
    "currency": "expense_currency",
    "transaction currency": "expense_currency",

    # Dates
    "trip_date": "trip_date",
    "travel date": "trip_date",
    "departure date": "trip_date",
    "check-in date": "trip_date",
    "transaction date": "trip_date",
    "booking date": "trip_date",

    # Ground transport
    "transport_type": "transport_type",
    "transport type": "transport_type",
    "vehicle type": "transport_type",
    "ground type": "transport_type",
}

# Concur expense type codes → our trip_type values
EXPENSE_TYPE_MAP = {
    "airfr": "flight",
    "air fare": "flight",
    "airfare": "flight",
    "air travel": "flight",
    "flight": "flight",
    "hotel": "hotel",
    "lodging": "hotel",
    "accommodation": "hotel",
    "carrt": "car_rental",
    "car rental": "car_rental",
    "car hire": "car_rental",
    "taxi": "taxi",
    "cab": "taxi",
    "uber": "taxi",
    "lyft": "taxi",
    "train": "rail",
    "rail": "rail",
    "railway": "rail",
    "ground": "ground",
    "ground transport": "ground",
    "mileage": "car_rental",
}


def _normalize_column(col: str) -> str:
    cleaned = col.strip().lower()
    return COLUMN_ALIASES.get(cleaned, re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_"))


def _normalize_trip_type(raw_type: str) -> str:
    """Map Concur expense type codes to our canonical trip types."""
    key = raw_type.strip().lower()
    return EXPENSE_TYPE_MAP.get(key, key)


def parse_corporate_travel_csv(file_content: bytes) -> Iterator[Dict]:
    """
    Parse a Concur/Navan corporate travel CSV export.

    Yields one dict per travel record row.
    """
    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    for raw_row in reader:
        # Normalize column names
        row = {_normalize_column(k): v.strip() for k, v in raw_row.items() if k}

        # Normalize trip type from Concur expense type codes
        if "trip_type" in row and row["trip_type"]:
            row["trip_type"] = _normalize_trip_type(row["trip_type"])

        # Skip empty rows
        if not any(row.values()):
            continue

        yield row
