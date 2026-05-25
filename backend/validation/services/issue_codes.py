"""
Validation issue codes — centralized constants.

Keeping codes as string constants (not integer enums or DB lookups) means:
- API responses include readable codes without join overhead
- Frontend can show different UI per code type without a secondary API call
- New codes are added by adding a line here, no migration needed
"""


class IssueCode:
    # Shared across all source types
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
    AMBIGUOUS_DATE = "AMBIGUOUS_DATE"
    NEGATIVE_VALUE = "NEGATIVE_VALUE"
    ZERO_VALUE = "ZERO_VALUE"
    DUPLICATE_ROW = "DUPLICATE_ROW"
    UNKNOWN_UNIT = "UNKNOWN_UNIT"

    # SAP Fuel specific
    UNKNOWN_FUEL_TYPE = "UNKNOWN_FUEL_TYPE"
    UNREALISTIC_QUANTITY = "UNREALISTIC_QUANTITY"

    # Utility Electricity specific
    OVERLAPPING_BILLING_PERIOD = "OVERLAPPING_BILLING_PERIOD"
    BILLING_END_BEFORE_START = "BILLING_END_BEFORE_START"
    CONSUMPTION_TOO_HIGH = "CONSUMPTION_TOO_HIGH"
    MISSING_METER_ID = "MISSING_METER_ID"

    # Corporate Travel specific
    INVALID_IATA_CODE = "INVALID_IATA_CODE"
    MISSING_AIRPORT_CODE = "MISSING_AIRPORT_CODE"
    UNREALISTIC_DISTANCE = "UNREALISTIC_DISTANCE"
    SAME_DEPARTURE_ARRIVAL = "SAME_DEPARTURE_ARRIVAL"
    MISSING_TRIP_TYPE = "MISSING_TRIP_TYPE"
    UNKNOWN_CABIN_CLASS = "UNKNOWN_CABIN_CLASS"
