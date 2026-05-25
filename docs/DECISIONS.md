# DECISIONS.md — Engineering Decisions & Rationale

Every decision listed here was made deliberately. This document is intended to answer "why did you do X?" before the question is asked.

---

## Source Format Selection

### SAP: Why the flat-file / ALV export format?

SAP has four main ways to get data out: IDoc, BAPI/RFC, OData service, and flat-file ALV report download.

**We chose flat-file (CSV) for these reasons:**

1. **Access level**: IDoc and BAPI require an SAP Basis admin to configure outbound interfaces. Most clients who send us data are not giving us direct SAP access. The flat file is what a procurement manager emails us.

2. **Reality of client onboarding**: In practice, an ESG platform receives manual CSV exports from client-side SAP users for 80% of clients. OData integration is a later maturity level.

3. **What we chose to ignore**: SAP IDoc format (MATMAS, DEBMAS) — too client-specific. OData (SAP Fiori) — requires SAP S/4HANA, not all clients are on S/4. BAPI RFC — requires VPN/network access to client SAP system.

**What this means in practice:** Our parser handles the German-locale SAP ALV export (MB51 material documents, ME2M purchasing documents). Column names may be in German (`Buchungsdatum` → `transaction_date`), dates are `DD.MM.YYYY`, numbers use European format (`1.234,56`), and the delimiter is semicolon rather than comma.

---

### Utility Electricity: Why CSV upload instead of API pull?

Utility providers in India (BESCOM, Tata Power, BSES, MSEDCL, TANGEDCO) do not have public APIs. Even in markets with APIs (PG&E in the US, National Grid in the UK), API access requires:
- OAuth credentials per account
- Account-level authorization from the client
- Different API formats per utility

**We chose portal CSV export because:**
- Facilities managers can already download these from their utility portal
- It requires no API credentials
- It's what actually happens at 90% of clients

**What we rejected:**
- PDF bill parsing (OCR): PDFs are not machine-readable — Tesseract or a commercial API would be needed, adding infra complexity and unreliability. Noted in TRADEOFFS.md.
- Scraping the portal: Fragile, legally questionable, breaks when portals update.
- Email parsing (forwarding utility bills): Interesting but scope creep.

**Format challenge we handle:** Billing periods that don't align to calendar months (15-Jan to 14-Feb is common). We store exact billing_start and billing_end dates rather than normalizing to month buckets.

---

### Corporate Travel: Why CSV upload over Concur/Navan API?

Both Concur and Navan have APIs:
- Concur has a SAP Concur API (OAuth 2.0, REST)
- Navan has an expense export API

**We chose CSV upload because:**
1. API credentials require client IT involvement — significant friction for a prototype
2. Concur's API has rate limits and a complex auth flow (company-level OAuth tokens)
3. The data we need (trip type, airports, distance, cabin class, amount) is fully available in their standard CSV export
4. Navan and Concur CSV exports have slightly different schemas — we handle both via column alias mapping

**What the Concur SAE (Standard Accounting Extract) format looks like:**
- Fixed column set but configurable per company
- Expense type codes: AIRFR (airfare), HOTEL, CARRT (car rental)
- Class of service: COACH, BUSINESS, FIRST, PREMIUM_ECONOMY
- Distance: not always included — sometimes only origin/destination airports
- Multiple currencies: expense currency + company reimbursement currency

**Key challenge we handle:** IATA vs ICAO code confusion. Travelers sometimes enter 4-letter ICAO codes (KJFK) instead of 3-letter IATA codes (JFK). We detect this and flag it with `INVALID_IATA_CODE`. We also map city names ("Mumbai", "New Delhi") to IATA codes via a lookup table.

---

## Ingestion Architecture: Synchronous vs Async

**We chose synchronous ingestion (processing in the HTTP request) instead of Celery + Redis.**

Justification:
- CSV files in this context are < 10MB, typically 1,000–5,000 rows
- Processing time: < 5 seconds for 5,000 rows
- Synchronous processing returns immediate results to the analyst
- Celery adds: a Redis broker, a Celery worker process, a flower monitoring tool, a separate deployment target, and significant operational complexity
- If files grow to 100k+ rows, adding async is a targeted change in the pipeline service — the rest of the architecture doesn't need to change

**The right way to think about this:** Async task queues solve a real problem (don't block HTTP workers on long tasks). At our file sizes, that problem doesn't exist yet. Adding Celery before it's needed is overengineering.

---

## Status Model: Denormalization Decision

`RawRecord.status` is denormalized — the canonical history is in `ApprovalAction`, but we store the current status on `RawRecord` for query performance.

**Why this tradeoff is acceptable:**
- Dashboard queries (`SELECT COUNT(*) WHERE status = 'suspicious'`) would be expensive if they required joining and aggregating over `ApprovalAction`
- Status changes always write both: `RawRecord.status` update + `AuditLog` entry + `ApprovalAction` row
- Enforced in the service layer (`approval_service.py`) — not ad-hoc in views
- If denormalization gets out of sync (bug), the AuditLog + ApprovalAction table is the source of truth to rebuild from

---

## Emission Factors: Why Hardcoded Constants

Emission factors should be versioned DB rows in production (with `effective_from` dates), because:
- Factors are updated annually (DESNZ publishes new values every June)
- GHG reports reference the factor valid at the time of activity, not today's factor
- A CO2e number calculated in 2024 should use 2024 factors even if viewed in 2026

**Why we hardcoded them in the prototype:**
- Implementing factor versioning correctly is a significant feature (not a small addition)
- It requires: a FactorVersion table, factor lookups by activity date, UI for factor management, migration scripts for factor updates
- All of this would obscure the core data pipeline logic being evaluated here
- We document the gap explicitly and explain the production approach

---

## Authentication: Why We Skipped It

We store `uploaded_by` as a plain string instead of a FK to a Django User.

**Why this is the right call for a prototype:**
- Auth is a full feature: user model, login/logout, sessions or JWT, role management, password reset
- The assignment evaluates ingestion pipeline quality, not auth implementation
- A production auth system would be: Django Allauth + DRF token auth, or a third-party auth provider (Auth0, Firebase Auth)
- We document this clearly: `analyst_name` is a string, not a user object

**What we'd add in production:**
```python
analyst = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
```

---

## What We Chose NOT to Build

1. **Celery/Redis async pipeline**: Justified above. File sizes don't warrant it.
2. **OCR/PDF utility bill parsing**: Requires Tesseract or commercial API, unreliable output.
3. **Multi-file batch upload**: One file per batch keeps the status machine simple and the UI clear.
4. **Real-time WebSocket updates**: Polling (30s) is sufficient for analyst workflow.
5. **Multi-currency conversion**: Travel expense amounts stored in original currency, conversion noted as a gap.
6. **Kubernetes/Docker Compose**: Render/Vercel handles infra; container orchestration is scope creep.
7. **Cross-batch duplicate detection**: Complex query, needs indexing strategy. Noted in TRADEOFFS.md.
8. **Factor versioning**: See above. Documented gap.

---

## What We'd Ask the PM

1. **Grid emission factor per facility**: The CO2e for electricity depends on the grid region. Do we maintain a facility → country mapping, or should clients provide it with each upload?

2. **Billing period mismatch**: Utility bills often don't align to calendar quarters. For Scope 2 reporting, should we pro-rate across months, or report by billing period?

3. **Scope 3 Category boundaries**: Corporate travel is Scope 3 Category 6. But some clients also have freight (Category 4) and upstream supply chain (Category 1). Should we expand the source types?

4. **Approval hierarchy**: Should there be a two-step approval (analyst → manager)? Currently any analyst can approve any record.

5. **Historical re-processing**: If emission factors update (e.g., 2024 → 2025 DESNZ values), should we re-calculate historical records' CO2e? Or freeze them at the factor valid at ingestion time?
