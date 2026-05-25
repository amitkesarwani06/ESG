"""
SAP Fuel & Procurement validator.

SAP flat-file exports (IDoc or standard download) are notoriously messy.
What we handle here:
- Column names may be German or English depending on SAP system locale
- Dates in DD.MM.YYYY (German default) or MM/DD/YYYY (US)
- Units may be SAP internal UoM codes (e.g., 'L', 'LTR', 'GAL', 'M3')
- plant_code may include leading zeros (SAP pads to 4 digits)
- quantity may have comma-as-decimal-separator (European locale)
- material_code follows SAP 18-character format but may be truncated

REQUIRED fields we enforce: plant_code, fuel_type, quantity, unit, transaction_date
OPTIONAL but validated: vendor, material_code
"""
import re
from .base_validator import BaseValidator, ValidationResult
from .issue_codes import IssueCode
from emissions.factors import SAP_FUEL_TYPE_ALIASES, FUEL_FACTORS_KG_CO2E_PER_LITRE

# All SAP UoM codes we can handle — anything else is flagged UNKNOWN_UNIT
KNOWN_UNITS = {
    "L", "LTR", "LITRE", "LITRES", "LITER",
    "GAL", "GALLON", "GALLONS",
    "KG", "KGS", "KILOGRAM",
    "TON", "TONS", "T", "MT",
    "M3", "CBM", "CUMT",
    "MMBTU", "BTU",
}


class SAPFuelValidator(BaseValidator):
    """
    Validates a single row from a SAP fuel/procurement CSV export.

    The row dict has already been through the parser's column normalization
    (German column names mapped to snake_case English equivalents), so we
    work with standardized key names here.
    """

    # Fields that must be present for a row to be usable at all
    REQUIRED_FIELDS = ["plant_code", "fuel_type", "quantity", "unit", "transaction_date"]

    def validate_row(self, row: dict) -> ValidationResult:
        result = ValidationResult()

        # 1. Required fields check
        self._check_required(row, self.REQUIRED_FIELDS, result)

        # 2. Quantity must be non-negative
        self._check_non_negative(row, "quantity", result)

        # 3. Unit must be one we know how to convert
        unit = str(row.get("unit", "")).strip().upper()
        if unit and unit not in KNOWN_UNITS:
            result.add_error(
                code=IssueCode.UNKNOWN_UNIT,
                field_name="unit",
                message=f"Unit '{unit}' is not recognized. Known units: {', '.join(sorted(KNOWN_UNITS))}"
            )

        # 4. Fuel type must be one we have an emission factor for
        fuel_type = str(row.get("fuel_type", "")).strip().lower()
        if fuel_type and fuel_type not in SAP_FUEL_TYPE_ALIASES:
            result.add_warning(
                code=IssueCode.UNKNOWN_FUEL_TYPE,
                field_name="fuel_type",
                message=(
                    f"Fuel type '{fuel_type}' is not in our emission factor table. "
                    f"CO2e will not be calculated. Known types: {', '.join(sorted(SAP_FUEL_TYPE_ALIASES.keys()))}"
                )
            )

        # 5. Quantity sanity check — flag if unrealistically large
        try:
            qty = float(str(row.get("quantity", 0)).replace(",", ".").strip())
            if qty > 1_000_000:
                result.add_warning(
                    code=IssueCode.UNREALISTIC_QUANTITY,
                    field_name="quantity",
                    message=(
                        f"Quantity {qty} seems very large for a single transaction. "
                        f"Possible unit error or aggregated export?"
                    )
                )
        except (ValueError, TypeError):
            pass  # Already caught by _check_non_negative

        # 6. Date format validation (date parsing done in normalizer,
        #    but we flag unparseable dates here)
        date_str = str(row.get("transaction_date", "")).strip()
        if date_str and not self._is_parseable_date(date_str):
            result.add_error(
                code=IssueCode.INVALID_DATE_FORMAT,
                field_name="transaction_date",
                message=f"Cannot parse date: '{date_str}'. Expected formats: DD.MM.YYYY, YYYY-MM-DD, MM/DD/YYYY"
            )

        return result

    @staticmethod
    def _is_parseable_date(date_str: str) -> bool:
        """Check if the date string matches any format we support."""
        import re
        patterns = [
            r"^\d{4}-\d{2}-\d{2}$",               # ISO: 2024-01-15
            r"^\d{2}\.\d{2}\.\d{4}$",              # German SAP: 15.01.2024
            r"^\d{2}/\d{2}/\d{4}$",                # US: 01/15/2024
            r"^\d{2}-[A-Za-z]{3}-\d{4}$",          # Oracle-style: 15-JAN-2024
        ]
        return any(re.match(p, date_str) for p in patterns)
