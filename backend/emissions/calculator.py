"""
CO2e calculator using emission factors.

Each calculate_* function returns (co2e_kg: float | None, notes: str).
The notes explain which factor was used — important for auditor transparency.
Returning None means we couldn't calculate (missing data).
"""
from decimal import Decimal
from .factors import (
    FUEL_FACTORS_KG_CO2E_PER_LITRE,
    FUEL_FACTORS_KG_CO2E_PER_KG,
    ELECTRICITY_FACTORS_KG_CO2E_PER_KWH,
    FLIGHT_FACTORS_KG_CO2E_PER_PKM,
    HOTEL_FACTOR_KG_CO2E_PER_NIGHT,
    GROUND_TRANSPORT_FACTORS_KG_CO2E_PER_KM,
    SAP_FUEL_TYPE_ALIASES,
)


def calculate_fuel_co2e(fuel_type: str, quantity: float, unit: str) -> tuple:
    """
    Calculate CO2e for fuel combustion (Scope 1).

    Args:
        fuel_type: normalized fuel type string
        quantity: amount of fuel
        unit: 'L' (litres) or 'kg'

    Returns:
        (co2e_kg, notes) tuple
    """
    canonical = SAP_FUEL_TYPE_ALIASES.get(fuel_type.lower().strip(), None)
    if canonical is None:
        return None, f"Unknown fuel type: '{fuel_type}' — no emission factor applied"

    if unit == "L":
        factor = FUEL_FACTORS_KG_CO2E_PER_LITRE.get(canonical)
        unit_label = "kg CO2e/L"
    elif unit == "kg":
        factor = FUEL_FACTORS_KG_CO2E_PER_KG.get(canonical)
        unit_label = "kg CO2e/kg"
    else:
        return None, f"Unsupported unit for fuel calculation: '{unit}'"

    if factor is None:
        return None, f"No factor for fuel '{canonical}' in unit '{unit}'"

    co2e = quantity * factor
    notes = (
        f"Fuel: {canonical}, Qty: {quantity} {unit}, "
        f"Factor: {factor} {unit_label} (UK DESNZ 2023) → {co2e:.4f} kg CO2e"
    )
    return round(co2e, 4), notes


def calculate_electricity_co2e(consumption_kwh: float, country_code: str = "DEFAULT") -> tuple:
    """
    Calculate CO2e for purchased electricity (Scope 2).

    Uses location-based method (grid emission factor).
    Market-based method (using RECs/GOs) is out of scope for this prototype.
    """
    factor = ELECTRICITY_FACTORS_KG_CO2E_PER_KWH.get(
        country_code.upper(),
        ELECTRICITY_FACTORS_KG_CO2E_PER_KWH["DEFAULT"]
    )
    co2e = consumption_kwh * factor
    notes = (
        f"Electricity: {consumption_kwh} kWh, Country: {country_code}, "
        f"Factor: {factor} kg CO2e/kWh (IEA 2022, location-based) → {co2e:.4f} kg CO2e"
    )
    return round(co2e, 4), notes


def calculate_flight_co2e(distance_km: float, cabin_class: str) -> tuple:
    """
    Calculate CO2e for business flights (Scope 3).

    Radiative Forcing Index (RFI) is NOT applied here — this is conservative.
    UK DESNZ 2023 includes RFI in their air travel factors by default.
    """
    cabin_key = cabin_class.lower().strip().replace(" ", "_") if cabin_class else "unknown"
    factor = FLIGHT_FACTORS_KG_CO2E_PER_PKM.get(
        cabin_key,
        FLIGHT_FACTORS_KG_CO2E_PER_PKM["unknown"]
    )
    co2e = distance_km * factor
    notes = (
        f"Flight: {distance_km} km, Cabin: {cabin_class or 'unknown'}, "
        f"Factor: {factor} kg CO2e/pkm (UK DESNZ 2023) → {co2e:.4f} kg CO2e"
    )
    return round(co2e, 4), notes


def calculate_hotel_co2e(nights: int) -> tuple:
    """Calculate CO2e for hotel stays (Scope 3)."""
    co2e = nights * HOTEL_FACTOR_KG_CO2E_PER_NIGHT
    notes = (
        f"Hotel: {nights} nights × {HOTEL_FACTOR_KG_CO2E_PER_NIGHT} kg CO2e/night "
        f"(UK DESNZ 2023) → {co2e:.4f} kg CO2e"
    )
    return round(co2e, 4), notes


def calculate_ground_transport_co2e(distance_km: float, transport_type: str) -> tuple:
    """Calculate CO2e for ground transport (Scope 3)."""
    transport_key = transport_type.lower().strip() if transport_type else "unknown"
    factor = GROUND_TRANSPORT_FACTORS_KG_CO2E_PER_KM.get(
        transport_key,
        GROUND_TRANSPORT_FACTORS_KG_CO2E_PER_KM["unknown"]
    )
    co2e = distance_km * factor
    notes = (
        f"Ground: {distance_km} km, Type: {transport_type or 'unknown'}, "
        f"Factor: {factor} kg CO2e/km (UK DESNZ 2023) → {co2e:.4f} kg CO2e"
    )
    return round(co2e, 4), notes
