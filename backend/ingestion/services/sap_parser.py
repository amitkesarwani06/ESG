"""
SAP Fuel & Procurement CSV parser.

SAP flat-file exports (SE16, MB51, ME2M transactions) are non-standard CSV.
What makes them messy in practice:

1. Column headers in German or English depending on system locale:
   "Werk" vs "Plant", "Buchungsdatum" vs "Posting Date"

2. Headers may have extra spaces or special characters

3. The file may have metadata rows at the top (title, report name, filter criteria)
   before the actual column headers

4. SAP sometimes exports with a pipe (|) delimiter instead of comma

5. Numbers use European format: 1.234,56 means 1234.56

6. Trailing delimiter at end of each row (SAP quirk)

Our approach: try multiple delimiters, skip metadata rows, map known
German column names to English equivalents.

Reference: SAP Note 36735 — Standard Export formats for ALV reports
"""
import csv
import io
import re
from typing import Iterator, Dict

# Mapping of SAP German column names → our internal snake_case names
# Covers common transaction types: MB51 (Material Documents), ME2M (Purchase Orders)
GERMAN_COLUMN_MAP = {
    # Plant / Facility
    "Werk": "plant_code",
    "Werksname": "plant_name",
    "Plant": "plant_code",

    # Material / Fuel
    "Material": "material_code",
    "Materialbeschreibung": "fuel_type",
    "Material Description": "fuel_type",
    "Kurztext": "fuel_type",
    "Short Text": "fuel_type",

    # Quantity and Unit
    "Menge": "quantity",
    "Quantity": "quantity",
    "Basismengeneinheit": "unit",
    "Base Unit of Measure": "unit",
    "ME": "unit",
    "Mengeneinheit": "unit",
    "Unit of Entry": "unit",
    "Entnahmemenge": "quantity",

    # Dates
    "Buchungsdatum": "transaction_date",
    "Posting Date": "transaction_date",
    "Belegdatum": "transaction_date",
    "Document Date": "transaction_date",
    "Datum": "transaction_date",

    # Vendor
    "Lieferant": "vendor",
    "Vendor": "vendor",
    "Lieferantenname": "vendor",
    "Vendor Name": "vendor",

    # Additional fields
    "Bewegungsart": "movement_type",
    "Movement Type": "movement_type",
    "Einkaufsbeleg": "po_number",
    "Purchasing Document": "po_number",
}


def _detect_delimiter(sample: str) -> str:
    """Sniff the delimiter from the first few rows of the file."""
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","  # Default to comma


def _find_header_row(lines: list) -> int:
    """
    Find the index of the actual column header row.

    SAP ALV reports often have 2-5 lines of report metadata before headers.
    We identify the header row by looking for the first row that contains
    a high proportion of our known column names.
    """
    known_cols = set(GERMAN_COLUMN_MAP.keys()) | {
        "plant_code", "fuel_type", "quantity", "unit",
        "transaction_date", "vendor", "material_code"
    }

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        # Check if this line contains at least 2 known column names
        cols = [c.strip() for c in re.split(r"[,;\t|]", line)]
        matches = sum(1 for c in cols if c in known_cols)
        if matches >= 2:
            return i

    return 0  # Fallback: assume first row is header


def _normalize_column_name(col: str) -> str:
    """
    Convert a SAP column name to our internal snake_case name.
    Falls back to a sanitized version of the original.
    """
    cleaned = col.strip()
    if cleaned in GERMAN_COLUMN_MAP:
        return GERMAN_COLUMN_MAP[cleaned]
    # Fallback: lowercase, replace spaces/special chars with underscores
    return re.sub(r"[^a-z0-9]+", "_", cleaned.lower()).strip("_")


def parse_sap_fuel_csv(file_content: bytes) -> Iterator[Dict]:
    """
    Parse a SAP fuel/procurement CSV file.

    Yields one dict per data row with normalized key names.
    Skips empty rows and SAP metadata rows.

    Args:
        file_content: raw bytes of the uploaded CSV file

    Yields:
        dict with snake_case keys for each valid data row
    """
    # Decode with UTF-8, fallback to Latin-1 (SAP German exports)
    try:
        text = file_content.decode("utf-8-sig")  # -sig handles BOM
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    lines = text.splitlines()
    if not lines:
        return

    # Detect delimiter from first non-empty lines
    sample = "\n".join(lines[:10])
    delimiter = _detect_delimiter(sample)

    # Find actual header row (skip SAP metadata)
    header_row_idx = _find_header_row(lines)
    header_line = lines[header_row_idx]
    raw_headers = [h.strip() for h in header_line.split(delimiter)]
    normalized_headers = [_normalize_column_name(h) for h in raw_headers]

    # Parse data rows
    for line in lines[header_row_idx + 1:]:
        if not line.strip():
            continue

        values = list(csv.reader([line], delimiter=delimiter))[0]

        # Skip SAP subtotal/total rows (often have "Total" or "**" in first column)
        if values and (values[0].strip().startswith("*") or
                       values[0].strip().lower() in ("total", "gesamt", "summe")):
            continue

        # Pad or truncate to header length
        while len(values) < len(normalized_headers):
            values.append("")
        values = values[:len(normalized_headers)]

        row = dict(zip(normalized_headers, values))

        # Strip trailing whitespace from all values
        row = {k: v.strip() for k, v in row.items()}

        # Skip rows where all meaningful fields are empty
        key_fields = ["plant_code", "quantity", "transaction_date"]
        if all(not row.get(f, "").strip() for f in key_fields):
            continue

        yield row
