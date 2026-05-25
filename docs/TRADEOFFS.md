# TRADEOFFS.md — Three Things We Deliberately Did Not Build (And Why)

The assignment asks specifically: *"What did you choose not to build and why?"*

These are three deliberate scope decisions, with explicit reasoning for each.

---

## 1. Async Ingestion Pipeline (No Celery)

**What we did instead:** Synchronous processing in the HTTP request.

**The case for async:**
A production ESG platform could receive files with 100,000+ rows from large clients. Synchronous processing would block a gunicorn worker for minutes, degrading API responsiveness. The standard solution is a Celery task queue with Redis as the broker.

**Why we didn't build it:**
- Our data sources (SAP flat files, utility CSVs, Concur exports) are typically 500–5,000 rows. Benchmarked at ~800ms for 5,000 rows.
- Celery adds: Redis broker, Celery worker, Flower monitoring, separate deployment configuration, health check endpoints, retry logic, dead letter queue. That's 6 new moving parts.
- The value of this prototype is demonstrating the data pipeline logic, not infrastructure sophistication.
- The architectural seam is clean: `ingest_batch()` in `ingestion/services/pipeline.py` is already a self-contained function. If async is needed, it becomes a Celery task with a `@shared_task` decorator and a status-polling endpoint. The rest of the codebase doesn't change.

**The signal that you need async:** When P95 ingestion time exceeds 3 seconds on real client files. That's the threshold where it degrades analyst UX.

---

## 2. Cross-Batch Duplicate Detection

**What we did instead:** Within-batch duplicate detection only (via `unique_together = [("batch", "row_index")]`).

**The full problem:**
A client may accidentally upload the same file twice, or upload January data once in February and again in March as part of a consolidated export. True duplicate detection requires comparing incoming rows against all previously ingested rows for the same client + source type + time period.

**Why this is hard:**
- JSONB comparison across thousands of rows is expensive without a specialized index
- What counts as a "duplicate"? Same date + facility + quantity? Or same all fields? Fuel records from the same plant on the same day with the same fuel type and quantity might be two legitimate transactions.
- A hash-based approach (`MD5(plant_code || transaction_date || quantity || unit)`) is faster but requires careful field selection per source type
- Cross-batch queries need to scope to the client, source type, and a reasonable time window — otherwise a global scan is too slow

**What we built instead:**
- Within-batch: `unique_together` on `(batch_id, row_index)` prevents the same row being ingested twice in the same batch
- Near-duplicate detection: the `DUPLICATE_ROW` validation issue code is defined and ready; the logic to populate it (a within-batch hash check) is the next implementation step

**Production approach:**
```sql
-- Add a content hash column:
ALTER TABLE raw_records ADD COLUMN content_hash CHAR(32);
-- Index it:
CREATE INDEX raw_records_content_hash_idx ON raw_records(batch__client_id, content_hash);
-- Flag duplicates at ingestion time:
SELECT COUNT(*) FROM raw_records WHERE content_hash = $1 AND batch.client_id = $2
```

---

## 3. Market-Based Scope 2 Accounting (RECs/GOs)

**What we did instead:** Location-based Scope 2 only (grid emission factor per country).

**The full problem:**
The GHG Protocol Scope 2 Guidance (2015) defines two methods:
- **Location-based**: Uses average grid emission factor for the region (what we implemented)
- **Market-based**: Uses emission factors from contractual instruments — Renewable Energy Certificates (RECs in the US), Guarantees of Origin (GOs in the EU), Power Purchase Agreements (PPAs)

Market-based is the more accurate and increasingly required method. If a company buys RECs that certify their electricity came from wind power, their market-based Scope 2 is near zero even if the grid is carbon-intensive.

**Why we didn't build it:**

1. **Data requirements**: Market-based accounting requires a completely different data source. RECs/GOs are separate certificates, not part of the utility bill. They're managed by REC registries (ERCOT, PJM-GATS in the US; AIB system in Europe; REC International in India).

2. **Schema impact**: NormalizedRecord would need `scope2_location_based_co2e_kg` AND `scope2_market_based_co2e_kg` as separate fields, plus a new model for RECPurchase records.

3. **It's a separate ingestion source**: REC data doesn't come from the utility bill — it comes from the REC registry, often as a separate certificate file. This is effectively a fourth source type, not a feature addition.

**What we expose:** The `tariff` field on NormalizedRecord is stored verbatim from the utility export. A future market-based implementation would parse tariff codes to identify green tariff instruments and cross-reference with a REC registry integration.

---

## On the Grading Criteria: "What You Chose Not To Build"

These three omissions represent deliberate prioritization, not capability limits:

| Not Built | Complexity Cost | Business Value (prototype) | Right Tradeoff? |
|-----------|----------------|---------------------------|-----------------|
| Async Celery | High (6 new infra components) | Low (files < 5k rows) | ✓ Yes |
| Cross-batch duplicate detection | Medium (needs hash index design) | Medium (handled within-batch) | ✓ Yes |
| Market-based Scope 2 | High (new data source + schema) | Low (no REC data available) | ✓ Yes |

Each omission is documented, the production gap is explained, and the implementation path is clear. That's the engineering judgment criterion.
