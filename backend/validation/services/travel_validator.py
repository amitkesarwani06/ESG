"""
Corporate Travel validator.

Based on research into Concur and Navan export formats.

Concur exports (SAE format) include:
- Employee ID (as per HR system)
- Trip type: Air, Hotel, Car, Rail, Ground Transport
- IATA codes for flights
- Distance is often NOT provided — needs to be derived from IATA pairs
- Cabin class: Coach/Economy, Business, First, Premium Economy
- Expense amounts in expense currency + reimbursement currency

Navan exports are similar but use different column naming conventions.

Key validation challenges:
- IATA codes may be ICAO codes (4-letter) by mistake
- Distance may be 0 or missing — we calculate it if airports are known
- "Distance" in Concur is sometimes in miles, sometimes km — unit inconsistency
- Hotel nights may be missing; only check-in date provided
- Ground transport may have no distance at all (just expense amount)

Max realistic flight distance: ~19,800 km (Newark to Singapore)
Max realistic ground trip: ~1,000 km (would take a train instead)
"""
import re
from .base_validator import BaseValidator, ValidationResult
from .issue_codes import IssueCode

# IATA codes are always 3 uppercase letters
IATA_PATTERN = re.compile(r"^[A-Z]{3}$")

# Earth's circumference / 2 — absolute maximum possible distance
MAX_FLIGHT_DISTANCE_KM = 20_050
MAX_GROUND_DISTANCE_KM = 2_000  # Above this, you'd fly

VALID_CABIN_CLASSES = {"economy", "premium_economy", "business", "first", "coach"}
VALID_TRIP_TYPES = {"flight", "hotel", "ground", "rail", "car_rental", "taxi"}


class TravelValidator(BaseValidator):
    REQUIRED_FIELDS_FLIGHT = [
        "employee_id", "trip_type", "departure_airport",
        "arrival_airport", "trip_date"
    ]
    REQUIRED_FIELDS_HOTEL = ["employee_id", "trip_type", "trip_date", "facility"]
    REQUIRED_FIELDS_GROUND = ["employee_id", "trip_type", "trip_date"]

    def validate_row(self, row: dict) -> ValidationResult:
        result = ValidationResult()
        trip_type = str(row.get("trip_type", "")).strip().lower()

        # 1. Trip type must be known
        if not trip_type:
            result.add_error(
                code=IssueCode.MISSING_TRIP_TYPE,
                field_name="trip_type",
                message="trip_type is missing. Expected: flight, hotel, ground, rail, car_rental"
            )
            return result  # Can't do further type-specific validation

        if trip_type not in VALID_TRIP_TYPES:
            result.add_warning(
                code=IssueCode.MISSING_TRIP_TYPE,
                field_name="trip_type",
                message=f"Unrecognized trip_type '{trip_type}'. Expected: {', '.join(sorted(VALID_TRIP_TYPES))}"
            )

        # 2. Employee ID is always required
        if not str(row.get("employee_id", "")).strip():
            result.add_error(
                code=IssueCode.MISSING_REQUIRED_FIELD,
                field_name="employee_id",
                message="employee_id is required for all travel records."
            )

        # 3. Type-specific validation
        if trip_type == "flight":
            self._validate_flight(row, result)
        elif trip_type == "hotel":
            self._validate_hotel(row, result)
        else:
            self._validate_ground(row, result)

        return result

    def _validate_flight(self, row: dict, result: ValidationResult):
        dep = str(row.get("departure_airport", "")).strip().upper()
        arr = str(row.get("arrival_airport", "")).strip().upper()

        # Airport codes required for flights
        if not dep:
            result.add_error(
                code=IssueCode.MISSING_AIRPORT_CODE,
                field_name="departure_airport",
                message="departure_airport is required for flight records."
            )
        elif not IATA_PATTERN.match(dep):
            result.add_error(
                code=IssueCode.INVALID_IATA_CODE,
                field_name="departure_airport",
                message=(
                    f"'{dep}' is not a valid IATA code (3 uppercase letters). "
                    f"If this is an ICAO code (4 letters), it needs to be converted."
                )
            )

        if not arr:
            result.add_error(
                code=IssueCode.MISSING_AIRPORT_CODE,
                field_name="arrival_airport",
                message="arrival_airport is required for flight records."
            )
        elif not IATA_PATTERN.match(arr):
            result.add_error(
                code=IssueCode.INVALID_IATA_CODE,
                field_name="arrival_airport",
                message=f"'{arr}' is not a valid IATA code."
            )

        # Departure and arrival must be different
        if dep and arr and dep == arr:
            result.add_error(
                code=IssueCode.SAME_DEPARTURE_ARRIVAL,
                field_name="arrival_airport",
                message=f"Departure and arrival airport are both '{dep}'. Likely a data error."
            )

        # Distance validation (if provided)
        dist_str = str(row.get("distance_km", "")).strip()
        if dist_str:
            try:
                dist = float(dist_str.replace(",", ""))
                if dist < 0:
                    result.add_error(
                        code=IssueCode.NEGATIVE_VALUE,
                        field_name="distance_km",
                        message=f"Negative distance: {dist} km"
                    )
                elif dist > MAX_FLIGHT_DISTANCE_KM:
                    result.add_error(
                        code=IssueCode.UNREALISTIC_DISTANCE,
                        field_name="distance_km",
                        message=(
                            f"Distance {dist:.0f} km exceeds maximum possible flight distance "
                            f"({MAX_FLIGHT_DISTANCE_KM:,} km). Possible miles/km confusion?"
                        )
                    )
            except ValueError:
                result.add_error(
                    code=IssueCode.UNREALISTIC_DISTANCE,
                    field_name="distance_km",
                    message=f"distance_km is not a valid number: '{dist_str}'"
                )

        # Cabin class validation
        cabin = str(row.get("cabin_class", "")).strip().lower()
        if cabin and cabin not in VALID_CABIN_CLASSES:
            result.add_warning(
                code=IssueCode.UNKNOWN_CABIN_CLASS,
                field_name="cabin_class",
                message=(
                    f"Cabin class '{cabin}' not recognized. Defaulting to economy for CO2e. "
                    f"Known: {', '.join(sorted(VALID_CABIN_CLASSES))}"
                )
            )

    def _validate_hotel(self, row: dict, result: ValidationResult):
        # Nights must be positive if provided
        nights_str = str(row.get("nights", "")).strip()
        if nights_str:
            try:
                nights = int(nights_str)
                if nights <= 0:
                    result.add_error(
                        code=IssueCode.NEGATIVE_VALUE,
                        field_name="nights",
                        message=f"Hotel nights must be positive, got: {nights}"
                    )
                elif nights > 365:
                    result.add_warning(
                        code=IssueCode.UNREALISTIC_DISTANCE,  # reusing code
                        field_name="nights",
                        message=f"Hotel nights '{nights}' seems very high. Possible aggregation?"
                    )
            except ValueError:
                result.add_error(
                    code=IssueCode.NEGATIVE_VALUE,
                    field_name="nights",
                    message=f"Hotel nights is not an integer: '{nights_str}'"
                )

    def _validate_ground(self, row: dict, result: ValidationResult):
        # Distance is optional for ground transport (expense amount is fallback)
        dist_str = str(row.get("distance_km", "")).strip()
        if dist_str:
            try:
                dist = float(dist_str.replace(",", ""))
                if dist > MAX_GROUND_DISTANCE_KM:
                    result.add_warning(
                        code=IssueCode.UNREALISTIC_DISTANCE,
                        field_name="distance_km",
                        message=(
                            f"Ground transport distance {dist:.0f} km is unusually long. "
                            f"Did you mean to log this as a flight?"
                        )
                    )
            except ValueError:
                pass  # No distance provided — we'll use expense amount as fallback
