"""
Utility Electricity CSV parser.

Portal CSV exports from utility companies are generally cleaner than SAP
exports, but have their own inconsistencies. We've modeled this on exports
from common utility portals (BESCOM, Tata Power, PG&E, National Grid).

Key observations from real utility portal exports:
1. Column names vary by utility company (some use "Account Number" for meter ID)
2. Consumption may be labeled "Usage (kWh)", "Energy Consumed", "Units"
3. Billing period sometimes split into two columns, sometimes as a range string
   (e.g., "2024-01-01 to 2024-01-31")
4. Tariff structure may be tiered; exports show blended rate or breakdown

We use a header alias map similar to the SAP parser.
"""
import csv
import io
import re
from typing import Iterator, Dict

# Aliases from various utility portal column names → our internal names
COLUMN_ALIASES = {
    # Meter ID aliases
    "meter_id": "meter_id",
    "meter id": "meter_id",
    "meter number": "meter_id",
    "meter no": "meter_id",
    "account number": "meter_id",
    "account no": "meter_id",
    "service point": "meter_id",
    "supply point id": "meter_id",
    "mpan": "meter_id",  # UK Meter Point Administration Number

    # Consumption aliases
    "consumption_kwh": "consumption_kwh",
    "consumption (kwh)": "consumption_kwh",
    "usage (kwh)": "consumption_kwh",
    "energy consumed (kwh)": "consumption_kwh",
    "units consumed": "consumption_kwh",
    "net metered usage": "consumption_kwh",
    "kwh": "consumption_kwh",
    "energy (kwh)": "consumption_kwh",
    "total consumption": "consumption_kwh",

    # Billing period aliases
    "billing_start": "billing_start",
    "billing start": "billing_start",
    "bill start date": "billing_start",
    "from date": "billing_start",
    "period start": "billing_start",
    "service from": "billing_start",

    "billing_end": "billing_end",
    "billing end": "billing_end",
    "bill end date": "billing_end",
    "to date": "billing_end",
    "period end": "billing_end",
    "service to": "billing_end",
    "through": "billing_end",

    # Tariff
    "tariff": "tariff",
    "rate": "tariff",
    "rate plan": "tariff",
    "tariff code": "tariff",
    "rate code": "tariff",
    "schedule": "tariff",

    # Facility
    "facility": "facility",
    "location": "facility",
    "site": "facility",
    "site name": "facility",
    "premises": "facility",
    "address": "facility",
}


def _normalize_column(col: str) -> str:
    cleaned = col.strip().lower()
    return COLUMN_ALIASES.get(cleaned, re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_"))


def _try_split_period_range(row: dict) -> dict:
    """
    Handle utility exports that combine billing period in one column:
    e.g., "2024-01-01 to 2024-01-31" or "01/01/2024 - 01/31/2024"
    """
    # Look for a period range field
    for key in list(row.keys()):
        val = str(row.get(key, "")).strip()
        if not val:
            continue
        # Match "date1 to date2" or "date1 - date2"
        match = re.match(
            r"(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4})\s+(?:to|-)\s+(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            val, re.IGNORECASE
        )
        if match:
            row["billing_start"] = match.group(1)
            row["billing_end"] = match.group(2)
            break
    return row


def parse_utility_electricity_csv(file_content: bytes) -> Iterator[Dict]:
    """
    Parse a utility electricity CSV export.

    Yields one dict per billing record row.
    """
    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    for raw_row in reader:
        # Normalize column names
        row = {_normalize_column(k): v.strip() for k, v in raw_row.items() if k}

        # Try to split combined billing period fields
        row = _try_split_period_range(row)

        # Skip empty rows
        if not any(row.values()):
            continue

        yield row
