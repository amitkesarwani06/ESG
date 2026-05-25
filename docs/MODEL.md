# MODEL.md — Data Model Documentation

## Why This Model Exists

The central challenge in ESG data ingestion isn't carbon calculation — it's data provenance. An auditor, a regulator, or a future analyst needs to answer:

> *"Where did this number come from, when was it ingested, who approved it, and has it been modified?"*

Every modeling decision in this system is oriented toward answering that question.

---

## Layered Architecture

```
CSV File
    ↓
UploadBatch          ← file-level record (filename, date, who uploaded)
    ↓
RawRecord            ← one row per CSV row, immutable, raw_data as JSONB
    ↓
ValidationIssue      ← machine-generated flags (can have 0..n per record)
NormalizedRecord     ← cleaned, unit-converted interpretation (1:1 with raw)
    ↓
ApprovalAction       ← analyst decision (append-only)
AuditLog             ← system event trail (every state change)
```

---

## Entity Descriptions

### Client
Multi-tenancy anchor. Every batch and every record traces back to a client. Even though the prototype serves one client, leaving this out would make future multi-tenancy a schema migration rather than a query change.

### SourceType
Three source types, each mapped to a GHG Protocol scope:
- `sap_fuel` → Scope 1 (direct combustion)
- `utility_elec` → Scope 2 (purchased electricity)
- `corporate_travel` → Scope 3 (business travel)

Scope is stored on SourceType rather than hardcoded in application logic so it's visible in the API and database without code inspection.

### UploadBatch
One row per uploaded file. The key decision here is that we track the file separately from the rows. This means:
- We can answer "what was in the June upload vs the July upload?"
- Batch-level locking (lock all approved records together)
- Error reporting at file level vs row level

### RawRecord
**The most important model in the system.**

`raw_data JSONB` stores the original CSV row as a key-value dict. We deliberately do not parse it into typed columns at this stage. Reasons:

1. **Column names vary per SAP installation**: SAP exports can have German or English headers, different column sets per transaction type, and trailing pipe characters. Trying to parse all of this into a fixed schema would require a fragile column mapping table for every client × source combination.

2. **Immutability**: Once a RawRecord is created, `raw_data` is never modified. If our normalization logic has a bug, we can re-process from the original. If there's a legal dispute, we can prove what the source system sent us.

3. **JSONB is queryable**: PostgreSQL JSONB supports GIN indexes and `->` operators, so we don't lose query power by storing raw data this way.

`row_index` preserves the original row position in the CSV file, allowing an analyst to open the original spreadsheet to the same row.

`status` is a denormalized field — the source of truth is the sequence of `ApprovalAction` rows, but having status on `RawRecord` makes dashboard queries fast without aggregating over the approval history table.

### NormalizedRecord
Separated from RawRecord for clean separation of concerns:
- RawRecord = what we received (immutable)
- NormalizedRecord = our interpretation (re-generatable)

If the normalization algorithm changes (e.g., we update emission factors, or discover a unit conversion error), we can delete all NormalizedRecords for a batch and re-run normalization from the RawRecords.

All quantity fields use canonical units:
- Liquid fuels → **Litres (L)**
- Electricity → **kWh** (already standard for grid electricity)
- Distance → **Kilometres (km)**

`co2e_kg` is stored as a computed value, not recalculated on read. This means the CO2e number is locked to the emission factor values at the time of normalization — important for auditability.

`normalization_notes` is a text field that logs every transformation applied ("Converted 1000 GAL → 3785.41 L × 3.78541"). This is the paper trail for auditors asking "why does this row show 3785 L when the source said 1000 GAL?"

### ValidationIssue
Machine-generated flags. Key design decisions:
- `issue_code` is a string constant (e.g., "NEGATIVE_VALUE"), not a FK to an issue_types table. Readable in API responses without a join.
- `severity` distinguishes errors (row becomes SUSPICIOUS) from warnings (row stays PENDING but analyst should review)
- `field_name` identifies which specific CSV column caused the issue — critical for analyst UX

### ApprovalAction
**Append-only**. Never updated or deleted. Each analyst decision is a new row.

This differs from the simpler approach of just having a `approved_by` column on `RawRecord`. The append-only approach means:
- Full decision history (if an analyst approves then a manager overrides)
- Clear accountability per decision
- No "who set this?" ambiguity

### AuditLog
System-generated events for all state changes. Uses `entity_type + entity_id` as a polymorphic reference rather than separate FKs to every entity type. This keeps the audit log centralized and avoids a 10-table join schema.

`old_value / new_value` as JSONB snapshots the state before and after each change — useful for debugging and compliance reporting.

---

## Multi-Tenancy

Current implementation: `client_id` on `UploadBatch`. All raw records trace back to a batch which traces back to a client. API filtering by client is a two-table join.

Not implemented in this prototype: row-level security (PostgreSQL RLS) to enforce client isolation at the database level. This is the correct production approach but is out of scope.

---

## Scope 1/2/3 Classification

The GHG Protocol scope is stored on `SourceType.scope`. This means:
- Every NormalizedRecord can be scope-classified via a join to its batch's source type
- The API returns scope on source type, so the frontend can display it per record
- Aggregate CO2e queries can group by scope without application logic

We did **not** implement multi-scope records (e.g., a Scope 3 category 1 vs category 15 split) because that level of detail is beyond what the data sources provide in this prototype.

---

## Source-of-Truth Tracking

For every NormalizedRecord, the provenance chain is:
```
NormalizedRecord.raw_record
  → RawRecord.batch
    → UploadBatch.source_type  (which source system)
    → UploadBatch.client       (which enterprise client)
    → UploadBatch.filename     (which specific file)
    → UploadBatch.uploaded_at  (when it arrived)
    → UploadBatch.uploaded_by  (who uploaded it)
  → RawRecord.raw_data         (the original row, verbatim)
  → RawRecord.row_index        (which row in the file)
```

This chain is complete and queryable. No data lineage is lost.
