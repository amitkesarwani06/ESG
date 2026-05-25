# SOURCES.md — Research Notes on Each Data Source

## What This Document Covers

For each of the three data sources, this document records:
1. What real-world format we researched
2. What we learned about the actual shape of the data
3. Why our sample data looks the way it does
4. What would break in a real deployment

---

## Source 1: SAP Fuel & Procurement Data

### What We Researched

SAP has several ways to export fuel and procurement data:

- **IDoc (Intermediate Document)**: SAP's native EDI format. Structured XML-like segments. Used for system-to-system integration (e.g., SAP → SAP). Not what a human exports.
- **BAPI/RFC**: Remote Function Calls to extract data programmatically. Requires developer access and SAP Basis configuration.
- **OData**: SAP Fiori/S/4HANA API. Modern but only available on newer SAP versions.
- **ALV Report Download**: The everyday export. A user runs a SAP report (MB51 for material documents, ME2M for purchase orders) and clicks "Export to Spreadsheet" or "Export to Local File". This is what we handle.

### What the ALV Export Actually Looks Like

MB51 (Material Document List) — what procurement teams use for fuel tracking:

```
Buchungsdatum;Werk;Bewegungsart;Material;Kurztext;Menge;ME;Lieferant
15.01.2024;1001;101;MDF-DS-001;Dieselkraftstoff;5.000,00;L;0000100456
```

Key observations:
- **Delimiter is semicolon**, not comma (German SAP default)
- **Date is DD.MM.YYYY** (German locale), not ISO
- **Numbers use European format**: `5.000,00` means 5000.00 (period = thousands separator, comma = decimal)
- **Column names are in German**: Werk (Plant), Bewegungsart (Movement Type), Kurztext (Short Text)
- **Vendor is an SAP internal number**: `0000100456` — meaningless without the vendor master lookup table
- **Quantity uses SAP UoM codes**: `L` (litres), `KG` (kilograms), `M3` (cubic metres)
- **Plant code has leading zeros**: `1001` or `0001` depending on display format
- **SAP appends a total row** at the bottom starting with `*` or "Gesamt"

Some SAP installations have English column headers (US-locale), which is why we maintain a bidirectional alias map.

### Sample Data Design Decisions

Our `sap_fuel_export.csv` includes:
- **German column names** (Buchungsdatum, Werk, Kurztext, etc.)
- **Semicolon delimiter**
- **German date format** (DD.MM.YYYY)
- **Various fuel types** including a German name ("Dieselkraftstoff") and an unknown fuel ("Mystery Fuel" with unit "BARRELS")
- **Intentional bad rows**: negative quantity, zero quantity, missing quantity, unknown unit, unrealistic quantity (999,999 L)
- **SAP total row** ("Gesamt") at the bottom — parser should skip it
- **Different vendors**: Hindustan Petroleum, Indian Oil, GAIL India — realistic for Indian operations

### What Would Break in Real Deployment

1. **Vendor master lookup**: SAP exports vendor numbers (0000100456), not names. Without a vendor master table, vendor field is useless.
2. **Plant master lookup**: Plant code "1001" maps to a facility address via the SAP plant master. Without this, we can't geo-locate the emission.
3. **Material classification**: We map material codes to fuel types via free-text "Kurztext" (short description). But Kurztext is manually entered and inconsistent per plant.
4. **Multi-currency**: Some plants transact in local currencies; fuel prices in SAP are in local currency with an exchange rate. We don't handle this.
5. **Movement types**: SAP movement type 101 = goods receipt. 102 = reversal. 261 = goods issue. Our parser currently treats all movement types as consumption — reversals (102) should subtract from totals.

---

## Source 2: Utility Electricity Data

### What We Researched

Indian utility portals reviewed:
- **BESCOM** (Bangalore): https://bescom.karnataka.gov.in/ — provides bill download, meter reading history as CSV
- **Tata Power** (Mumbai): Portal CSV export with monthly billing data
- **BSES Rajdhani/Yamuna** (Delhi): Excel export of consumption history
- **TANGEDCO** (Chennai): PDF bills only (no CSV) — this is the PDF gap mentioned in TRADEOFFS.md
- **MSEDCL** (Maharashtra): CSV export from portal with account-level data

UK utilities for reference:
- **National Grid**: MPAN-based data downloads, UK format (DD/MM/YYYY)
- **British Gas**: Account CSV with `kWh Used`, `Unit Rate`, `Standing Charge`

### What the Export Actually Looks Like

BESCOM portal CSV (anonymized):
```
Account Number,Service Location,Meter Number,From Date,To Date,Units Consumed,Amount (Rs.)
10045,Marathahalli Industrial Area,MTR-BLR-001,01/01/2024,31/01/2024,125430,1254300
```

Tata Power format (different column names for same data):
```
Meter ID,Premises,Period Start,Period End,Energy (kWh),Rate,Bill Amount
```

Key observations:
- **Column names vary per utility** — same data, 3+ different column names
- **Billing periods don't align to months**: A typical commercial meter reads on the 15th of the month, giving 15-Jan to 14-Feb billing periods
- **Large commercial meters** are in kWh; industrial HT consumers may be in MWh — unit is often not stated
- **Net metering**: Solar-equipped facilities may show negative consumption (export credits) — these cause NEGATIVE_VALUE flags
- **MPAN/supply point IDs**: UK meters use MPAN (13-digit Meter Point Administration Number). Indian meters use account numbers that don't follow a standard format.

### Sample Data Design Decisions

Our `utility_electricity.csv`:
- **Mixed column name styles** (Meter ID, Facility, Consumption (kWh), etc.)
- **Multiple Indian utility portals** represented (BESCOM, Tata Power, BSES, TANGEDCO, MSEDCL)
- **Mixed date formats** across rows (01/01/2024, 2024-01-01, 01-Jan-2024)
- **Overlapping billing period** for MTR-BLR-002 — validator should flag this
- **Negative consumption** (MTR-MUM-001 February) — net metering credit
- **Missing consumption** (MTR-HYD-001) — validator should flag
- **Unrealistically high consumption** (MTR-CHN-001 at 850,000 kWh) — likely MWh confusion
- **Billing end before start** (MTR-PUN-001) — validator should flag

### What Would Break in Real Deployment

1. **PDF-only utilities**: TANGEDCO (Tamil Nadu) provides PDF bills only. Would need OCR or manual data entry. This is the primary ingestion gap for utility data.
2. **Multi-tariff billing**: Large industrial consumers have time-of-use tariffs (peak/off-peak). Exports may show consumption broken by tariff band. Our model stores a single `tariff` field.
3. **Power factor corrections**: HT consumers have kVAh metering (kVAh, not kWh) with power factor penalties. Our `consumption_kwh` field assumes kWh meters.
4. **Cross-utility meter aggregation**: A facility may have multiple meters from different utilities. Aggregation is a reporting concern, not ingestion, but the data model needs to support it.

---

## Source 3: Corporate Travel Data

### What We Researched

**Concur SAE (Standard Accounting Extract)**:
- Industry-standard export format for corporate expense systems
- Fixed 30+ column schema, configurable per company
- Expense types: AIRFR (airfare), HOTEL, CARRT (car rental), TRAIN, TAXI, MILEAG (personal mileage)
- Amounts in `TransactionCurrencyCode` + `ApprovedAmount` in company base currency
- Class of service: COACH, BUSINESS, FIRST, PREMIUM ECONOMY (the exact strings vary per company configuration)
- Distance: often absent for air travel — only origin/destination airport provided

**Navan (formerly TripActions)**:
- More modern format, JSON-available via API but CSV export is more common
- Includes a `carbon_footprint_kg` column (their estimate) — we ignore this and recalculate
- Better structured than Concur: consistent IATA codes, explicit trip type field
- Same data shape: employee, travel date, airports, class, amount

**What we learned:**
- IATA 3-letter codes (JFK, BOM, LHR) are standard for international airlines
- BUT: Concur often stores city names or common abbreviations that travelers enter manually
  - "New Delhi" instead of "DEL"
  - "Mumbai" instead of "BOM"
  - "NYC" instead of "JFK"
  - ICAO codes (KJFK, EGLL) instead of IATA (JFK, LHR)
- Distance is rarely provided for flights — needs to be calculated from airport pair using great-circle distance
- Hotel `nights` is sometimes not in the export — only check-in date, forcing a calculation from check-out date

### Sample Data Design Decisions

Our `travel_concur_export.csv`:
- **Concur column names** (Expense Type, Class of Service, etc.)
- **Realistic Indian corporate travel patterns**: BOM-DEL, BOM-LHR, BOM-SIN routes
- **City name instead of IATA**: "New Delhi" for DEL — validator flags INVALID_IATA_CODE
- **ICAO vs IATA confusion**: "KJFK" (ICAO) instead of "JFK" (IATA) — validator flags it
- **Miles instead of km** (one row has 13,400 miles labeled as such) — normalizer converts
- **Same departure and arrival airport** (BOM to BOM, row_index 12) — validator flags SAME_DEPARTURE_ARRIVAL
- **Zero hotel nights** — validator flags
- **Unrealistic distance** (50,000 km) — validator flags UNREALISTIC_DISTANCE
- **Various expense types**: Airfare, Car Rental, Taxi, Train, Hotel
- **Amounts in INR** — not converted (currency conversion is a noted gap)

### What Would Break in Real Deployment

1. **Distance calculation**: Without IATA pair → distance lookup, we can't calculate CO2e for flights when distance isn't in the export. Production would need a great-circle distance API (e.g., Open Topo Data or a local airport coordinates table).

2. **Carbon factor per route type**: UK DESNZ distinguishes short-haul from long-haul factors. Without knowing haul length (derived from distance), we use a single factor per cabin class.

3. **Personal vs. business travel**: Concur often includes both. We ingest all rows; filtering by cost center or policy type is an analyst responsibility.

4. **Trip splitting**: A single "trip" in Concur may be multiple expense line items (outbound + return flight + hotel + taxi). We treat each line item as a separate record — correct for emissions accounting, but the analyst may want a "trip view" grouped by trip ID.

5. **Duty of care data**: Some clients want to anonymize employee IDs before sending to ESG platforms. Our model stores employee_id as a plain string; if clients send anonymized IDs, attribution is lost.
