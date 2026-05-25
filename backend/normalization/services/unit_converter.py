"""
Unit converter for fuel quantities.

SAP Internal UoM codes → canonical units.

Why we always convert to canonical units before storing:
- Comparing 500 L of diesel to 200 GAL requires knowing the conversion.
  If we store raw units, every downstream query needs to handle them.
- CO2e calculation is simpler when all inputs are in the same unit.
- Auditors can see both the original (in raw_data JSONB) and canonical forms.

Canonical units:
  Liquid fuels → Litres (L)
  Solid fuels  → Kilograms (kg)
  Gas (volume) → Cubic metres (m3)
  Energy       → Megajoules (MJ)
  Electricity  → kWh
  Distance     → Kilometres (km)

Note: For electricity billing, kWh is already canonical — we don't convert
to Joules because the emission factor tables are specified in kg CO2e/kWh.
"""


class UnitConverter:
    # All conversions are to the canonical unit for that category
    # Format: (from_unit, to_unit): multiplier
    CONVERSIONS = {
        # Liquid volume → Litres
        ("LTR", "L"): 1.0,
        ("LITRE", "L"): 1.0,
        ("LITRES", "L"): 1.0,
        ("LITER", "L"): 1.0,
        ("GAL", "L"): 3.78541,     # US gallon
        ("GALLON", "L"): 3.78541,
        ("GALLONS", "L"): 3.78541,
        ("M3", "L"): 1000.0,       # cubic metre
        ("CBM", "L"): 1000.0,
        ("CUMT", "L"): 1000.0,
        ("L", "L"): 1.0,           # already canonical

        # Mass → Kilograms
        ("KGS", "kg"): 1.0,
        ("KILOGRAM", "kg"): 1.0,
        ("KG", "kg"): 1.0,
        ("TON", "kg"): 1000.0,
        ("TONS", "kg"): 1000.0,
        ("MT", "kg"): 1000.0,
        ("T", "kg"): 1000.0,
        ("LB", "kg"): 0.453592,    # Pound (rare but seen in some US SAP installs)
        ("LBS", "kg"): 0.453592,

        # Energy → Megajoules
        ("MMBTU", "MJ"): 1055.06,
        ("BTU", "MJ"): 0.00105506,
        ("MJ", "MJ"): 1.0,
        ("GJ", "MJ"): 1000.0,

        # Distance → Kilometres
        ("MI", "km"): 1.60934,     # Miles (Concur often reports in miles)
        ("MILE", "km"): 1.60934,
        ("MILES", "km"): 1.60934,
        ("KM", "km"): 1.0,
        ("M", "km"): 0.001,        # Metres (rare)
    }

    # Map raw SAP UoM codes to canonical unit category
    CANONICAL_UNIT = {
        "L": "L", "LTR": "L", "LITRE": "L", "LITRES": "L", "LITER": "L",
        "GAL": "L", "GALLON": "L", "GALLONS": "L",
        "M3": "L", "CBM": "L", "CUMT": "L",
        "KG": "kg", "KGS": "kg", "KILOGRAM": "kg",
        "TON": "kg", "TONS": "kg", "MT": "kg", "T": "kg",
        "LB": "kg", "LBS": "kg",
        "MMBTU": "MJ", "BTU": "MJ", "MJ": "MJ", "GJ": "MJ",
        "MI": "km", "MILE": "km", "MILES": "km", "KM": "km", "M": "km",
    }

    def convert(self, value: float, from_unit: str) -> tuple:
        """
        Convert a value to its canonical unit.

        Returns:
            (converted_value, canonical_unit, notes) or (value, from_unit, error_note)
        """
        from_unit_upper = from_unit.strip().upper()
        canonical = self.CANONICAL_UNIT.get(from_unit_upper)

        if canonical is None:
            return value, from_unit, f"Unknown unit '{from_unit}' — stored as-is without conversion"

        if from_unit_upper == canonical:
            return value, canonical, f"Already in canonical unit: {canonical}"

        key = (from_unit_upper, canonical)
        multiplier = self.CONVERSIONS.get(key)

        if multiplier is None:
            return value, from_unit, f"No conversion defined from '{from_unit}' to '{canonical}'"

        converted = value * multiplier
        notes = (
            f"Converted {value} {from_unit} → {converted:.4f} {canonical} "
            f"(× {multiplier})"
        )
        return converted, canonical, notes
