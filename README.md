# ESG Data Ingestion Platform

A production-style prototype for ingesting, validating, normalizing, and auditing ESG (Environmental, Social, Governance) data from enterprise sources.

Built for the **Breathe ESG** Tech Internship Assignment.

## Live Demo

| Service | URL |
|---------|-----|
| Frontend | *[Add Vercel URL after deploy]* |
| Backend API | *[Add Render URL after deploy]* |
| Admin Panel | `{backend-url}/admin/` |

---

## What This Does

Client companies send sustainability data from three enterprise sources. Each source has a different schema, inconsistent formats, and messy real-world data.

This system:
1. **Ingests** CSV uploads from SAP (fuel), utility portals (electricity), and travel platforms (Concur/Navan)
2. **Validates** each row — checks for missing fields, negative values, overlapping periods, invalid IATA codes, etc.
3. **Normalizes** units (GAL → L, miles → km), dates (DD.MM.YYYY → ISO), and codes (city names → IATA codes)
4. **Calculates CO₂e** using published emission factors (UK DESNZ 2023, IEA 2022)
5. **Flags suspicious rows** for analyst review
6. **Tracks analyst decisions** (approve / reject) with an immutable audit trail
7. **Locks approved records** for audit submission

---

## Architecture

```
Frontend (React + Vite)          Backend (Django REST Framework)
     Vercel                              Render
        │                                  │
        └─────────── HTTPS / REST ─────────┘
                                           │
                                     PostgreSQL
                                    (Render DB)
```

**Why a monolith, not microservices?** Right-sized for this use case. The data pipeline logic is cohesive — splitting it would add latency and shared-state problems with no benefit at this scale. See [DECISIONS.md](docs/DECISIONS.md).

---

## Data Sources

| Source | Scope | Format | Key Challenges |
|--------|-------|--------|----------------|
| SAP Fuel & Procurement | Scope 1 | ALV flat-file CSV (semicolon-delimited, German locale) | German column names, DD.MM.YYYY dates, European number format, SAP UoM codes |
| Utility Electricity | Scope 2 | Portal CSV export | Column name variations per utility, billing periods ≠ calendar months, kWh vs MWh confusion |
| Corporate Travel (Concur) | Scope 3 | SAE-style CSV | IATA vs ICAO confusion, city names instead of codes, miles vs km, missing distances |

---

## Validation Engine

Each source type has a dedicated validator that checks:

**SAP Fuel:**
- Missing required fields (plant_code, fuel_type, quantity, unit, transaction_date)
- Negative or zero quantity
- Unknown SAP unit codes (e.g., "BARRELS" is not a recognized SAP UoM)
- Unknown fuel types (no emission factor available)
- Unrealistically large quantities (possible unit error)
- Unparseable date formats

**Utility Electricity:**
- Missing meter_id, consumption_kwh, billing_start, billing_end
- Negative consumption (could be net metering — flagged as warning not error)
- Consumption > 500,000 kWh/month (likely MWh/kWh confusion)
- Billing end before billing start
- Overlapping billing periods for the same meter (within-batch)

**Corporate Travel:**
- Missing airport codes for flights
- Invalid IATA codes (not 3 uppercase letters)
- Same departure and arrival airport
- Distance > 20,050 km (Earth's circumference / 2)
- Ground transport distance > 2,000 km (should be a flight)
- Unknown cabin class (defaults to economy with warning)
- Zero or negative hotel nights

**Issue severity:**
- `error` → record becomes **SUSPICIOUS** (blocks approval without explicit analyst override)
- `warning` → record stays **PENDING** (analyst can approve directly)

---

## Status Workflow

```
[upload] → PENDING → [validation errors?]
                           │
                    ┌──────┴──────┐
                    │ yes         │ no
                    ▼             ▼
               SUSPICIOUS      PENDING
                    │             │
              analyst reviews     │
                    └──────┬──────┘
                           │ [approve]
                           ▼
                        APPROVED
                           │
                    [lock batch]
                           ▼
                         LOCKED  ← immutable, audit-ready
```

---

## Setup — Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or use SQLite for development)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL and secret key

# Run migrations
python manage.py migrate

# Seed source types
python manage.py shell -c "
from core.models import SourceType
SourceType.objects.get_or_create(code='sap_fuel', defaults={'label': 'SAP Fuel & Procurement', 'scope': 1})
SourceType.objects.get_or_create(code='utility_elec', defaults={'label': 'Utility Electricity', 'scope': 2})
SourceType.objects.get_or_create(code='corporate_travel', defaults={'label': 'Corporate Travel', 'scope': 3})
"

# Create admin user
python manage.py createsuperuser

# Start server
python manage.py runserver
```

Backend runs at: http://localhost:8000

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure API URL
echo "VITE_API_BASE_URL=http://localhost:8000/api" > .env

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:5173

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/batches/upload/` | Upload a CSV file |
| `GET` | `/api/batches/` | List all upload batches |
| `GET` | `/api/batches/{id}/` | Batch detail with status counts |
| `GET` | `/api/batches/{id}/records/` | Records for batch (filterable by status) |
| `GET` | `/api/records/{id}/` | Single record with issues + normalized data |
| `POST` | `/api/records/{id}/approve/` | Approve a record |
| `POST` | `/api/records/{id}/reject/` | Reject a record |
| `POST` | `/api/batches/{id}/lock/` | Lock all approved records in batch |
| `GET` | `/api/audit-log/` | Full audit trail |
| `GET` | `/api/stats/` | Dashboard statistics |
| `GET` | `/api/source-types/` | Available source types |

**Upload example:**
```bash
curl -X POST http://localhost:8000/api/batches/upload/ \
  -F "file=@sample_data/sap_fuel_export.csv" \
  -F "source_type_code=sap_fuel" \
  -F "client_slug=acme-corp" \
  -F "uploaded_by=Jane Smith"
```

---

## Deployment

### Backend → Render

1. Push to GitHub
2. Create a new Web Service on [Render](https://render.com)
3. Connect your repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn config.wsgi:application`
   - **Environment Variables**: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DJANGO_SETTINGS_MODULE=config.settings.production`
5. Add a PostgreSQL database from Render's dashboard
6. After first deploy, seed source types via Render Shell

### Frontend → Vercel

1. Import frontend directory to [Vercel](https://vercel.com)
2. Set environment variable: `VITE_API_BASE_URL=https://your-render-url.onrender.com/api`
3. Deploy

---

## Sample Data

Test files are in `sample_data/`. They contain intentional data quality issues:

| File | Source Type | Intentional Issues |
|------|------------|-------------------|
| `sap_fuel_export.csv` | sap_fuel | Negative qty, zero qty, unknown unit ("BARRELS"), unknown fuel type, missing qty, German locale |
| `utility_electricity.csv` | utility_elec | Overlapping billing periods, negative consumption, missing consumption, end before start |
| `travel_concur_export.csv` | corporate_travel | City name instead of IATA, ICAO vs IATA, miles vs km, same origin/destination, unrealistic distance |

---

## Engineering Documentation

- **[MODEL.md](docs/MODEL.md)** — Data model rationale, schema decisions, provenance chain
- **[DECISIONS.md](docs/DECISIONS.md)** — Every major engineering decision with justification
- **[TRADEOFFS.md](docs/TRADEOFFS.md)** — Three things deliberately not built, and why
- **[SOURCES.md](docs/SOURCES.md)** — Real-world research on each data source format

---

## Project Structure

```
esg-data-ingestion-platform/
├── backend/
│   ├── config/settings/       # base, development, production settings
│   ├── core/                  # Client, SourceType, UploadBatch models + views
│   ├── ingestion/             # RawRecord model + per-source CSV parsers
│   │   └── services/          # sap_parser, utility_parser, travel_parser, pipeline
│   ├── normalization/         # NormalizedRecord model + unit/date conversion
│   │   └── services/          # unit_converter, date_normalizer, normalizer
│   ├── validation/            # ValidationIssue model + per-source validators
│   │   └── services/          # base_validator, sap/utility/travel validators
│   ├── review/                # ApprovalAction, AuditLog models + approval service
│   └── emissions/             # CO2e factors + calculator (UK DESNZ 2023)
├── frontend/
│   └── src/
│       ├── api/               # Axios client + per-domain API modules
│       ├── components/        # Layout, upload zone, status badges, issue panel
│       └── pages/             # Dashboard, Upload, Batches, BatchDetail, AuditLog
├── sample_data/               # Realistic test CSVs with intentional quality issues
└── docs/                      # MODEL.md, DECISIONS.md, TRADEOFFS.md, SOURCES.md
```

---

## Emission Factor Sources

| Source | Used For | Reference |
|--------|----------|-----------|
| UK DESNZ 2023 Conversion Factors | Fuel combustion, business flights, ground transport, hotels | [gov.uk/desnz](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023) |
| IEA 2022 Electricity Factors | Grid electricity (location-based Scope 2) | [iea.org](https://www.iea.org/data-and-statistics/data-product/emissions-factors-2022) |
| IPCC AR5 GWPs | CO2e conversion basis | [ipcc.ch](https://www.ipcc.ch/assessment-report/ar5/) |

**Note**: Emission factors are hardcoded constants in this prototype. In production, they would be versioned database records with `effective_from` dates, allowing historical recalculation. See [TRADEOFFS.md](docs/TRADEOFFS.md).
