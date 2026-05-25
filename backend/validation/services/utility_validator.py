"""
Utility Electricity validator.

Utility portal CSV exports (e.g., from portal.comed.com, PG&E, BESCOM, etc.)
are typically cleaner than SAP exports, but have their own failure modes:

- Billing periods that don't align to calendar months (e.g., 15-Mar to 14-Apr)
- Overlapping billing periods for the same meter (data export glitch)
- Consumption values with implicit units (assumes kWh but not stated)
- Negative consumption on net metering credits (confusingly labeled)
- Meter IDs with leading zeros that get stripped by Excel

We handle overlapping period detection within the same batch only.
Cross-batch overlap detection is a production gap (noted in TRADEOFFS.md).
"""
from datetime import datetime, date
from .base_validator import BaseValidator, ValidationResult
from .issue_codes import IssueCode

# 744 hours/month × 3 phases × 1000 kW per phase = 2,232,000 kWh
# Flagging anything above 500,000 kWh/month as unrealistic for a single meter
MAX_REASONABLE_KWH_MONTHLY = 500_000


class UtilityElectricityValidator(BaseValidator):
    REQUIRED_FIELDS = ["meter_id", "consumption_kwh", "billing_start", "billing_end"]

    def __init__(self):
        # Track meter billing periods for overlap detection within a batch
        # meter_id → list of (start, end) date tuples
        self._meter_periods: dict = {}

    def validate_row(self, row: dict) -> ValidationResult:
        result = ValidationResult()

        # 1. Required fields
        self._check_required(row, self.REQUIRED_FIELDS, result)

        # 2. Consumption must be non-negative
        self._check_non_negative(row, "consumption_kwh", result)

        # 3. Consumption sanity check — very high values suggest unit error
        try:
            kwh = float(str(row.get("consumption_kwh", 0)).replace(",", "").strip())
            if kwh > MAX_REASONABLE_KWH_MONTHLY:
                result.add_warning(
                    code=IssueCode.CONSUMPTION_TOO_HIGH,
                    field_name="consumption_kwh",
                    message=(
                        f"Consumption {kwh:.0f} kWh exceeds {MAX_REASONABLE_KWH_MONTHLY:,} kWh "
                        f"threshold. Possible MWh/kWh unit confusion."
                    )
                )
        except (ValueError, TypeError):
            pass

        # 4. Parse and validate billing period dates
        start_date = self._parse_date(str(row.get("billing_start", "")))
        end_date = self._parse_date(str(row.get("billing_end", "")))

        if row.get("billing_start") and start_date is None:
            result.add_error(
                code=IssueCode.INVALID_DATE_FORMAT,
                field_name="billing_start",
                message=f"Cannot parse billing_start: '{row.get('billing_start')}'"
            )
        if row.get("billing_end") and end_date is None:
            result.add_error(
                code=IssueCode.INVALID_DATE_FORMAT,
                field_name="billing_end",
                message=f"Cannot parse billing_end: '{row.get('billing_end')}'"
            )

        # 5. End must be after start
        if start_date and end_date:
            if end_date <= start_date:
                result.add_error(
                    code=IssueCode.BILLING_END_BEFORE_START,
                    field_name="billing_end",
                    message=(
                        f"billing_end ({end_date}) must be after "
                        f"billing_start ({start_date})"
                    )
                )

            # 6. Overlap detection within this batch for same meter
            meter_id = str(row.get("meter_id", "")).strip()
            if meter_id:
                if self._has_overlap(meter_id, start_date, end_date):
                    result.add_error(
                        code=IssueCode.OVERLAPPING_BILLING_PERIOD,
                        field_name="billing_start",
                        message=(
                            f"Meter '{meter_id}' has overlapping billing period "
                            f"{start_date} to {end_date} with another row in this batch."
                        )
                    )
                else:
                    # Register this period for future overlap checks
                    self._meter_periods.setdefault(meter_id, []).append(
                        (start_date, end_date)
                    )

        return result

    def _has_overlap(self, meter_id: str, start: date, end: date) -> bool:
        """Check if this period overlaps any previously seen period for this meter."""
        existing_periods = self._meter_periods.get(meter_id, [])
        for existing_start, existing_end in existing_periods:
            # Two periods overlap if start1 < end2 AND start2 < end1
            if start < existing_end and existing_start < end:
                return True
        return False

    @staticmethod
    def _parse_date(date_str: str):
        """Try multiple date formats, return date object or None."""
        formats = [
            "%Y-%m-%d",    # ISO
            "%d/%m/%Y",    # UK utility portals
            "%m/%d/%Y",    # US utility portals
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
