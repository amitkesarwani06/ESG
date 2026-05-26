import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getBatch } from "../api/batches";
import { getBatchRecords } from "../api/records";
import { lockBatch } from "../api/batches";
import StatusBadge from "../components/records/StatusBadge";
import IssuePanel from "../components/records/IssuePanel";

export default function BatchDetail() {
  const { id } = useParams();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState("");
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [analystName, setAnalystName] = useState("");
  const [locking, setLocking] = useState(false);
  const [lockError, setLockError] = useState("");
  const [lockSuccess, setLockSuccess] = useState("");

  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ["batch", id],
    queryFn: () => getBatch(id),
  });

  const { data: recordsData, isLoading: recordsLoading, refetch: refetchRecords } = useQuery({
    queryKey: ["batch-records", id, statusFilter],
    queryFn: () => getBatchRecords(id, statusFilter ? { status: statusFilter } : {}),
  });

  const records = recordsData?.results || recordsData || [];

  const handleLock = async () => {
    if (!analystName.trim()) {
      setLockError("Please enter your name to lock the batch.");
      return;
    }
    setLocking(true);
    setLockError("");
    setLockSuccess("");
    try {
      const result = await lockBatch(id, analystName.trim());
      setLockSuccess(result.message);
      queryClient.invalidateQueries(["batch", id]);
      queryClient.invalidateQueries(["batch-records", id]);
      refetchRecords();
    } catch (err) {
      setLockError(err.response?.data?.detail || "Lock failed.");
    } finally {
      setLocking(false);
    }
  };

  if (batchLoading) {
    return <div className="loading-state"><div className="spinner" /> Loading batch...</div>;
  }

  if (!batch) {
    return <div className="alert alert-error">Batch not found.</div>;
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header items-center gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Link to="/batches" style={{ color: "var(--text-muted)", textDecoration: "none", fontSize: 13, marginRight: 4 }}>
            ← Batches
          </Link>
          <div>
            <h1 style={{ fontSize: 18, margin: 0 }}>{batch.filename}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1" style={{ fontSize: 12, color: "var(--text-muted)" }}>
              <span>Uploaded by {batch.uploaded_by}</span>
              <span style={{ opacity: 0.5 }}>•</span>
              <span>{new Date(batch.uploaded_at).toLocaleString()}</span>
              {batch.source_type && (
                <span className={`scope-badge scope-${batch.source_type.scope}`} style={{ marginLeft: 4 }}>
                  S{batch.source_type.scope} · {batch.source_type.label}
                </span>
              )}
            </div>
          </div>
        </div>
        <StatusBadge status={batch.status} />
      </div>

      {/* Stats bar */}
      <div className="stat-grid" style={{ marginBottom: 20 }}>
        {[
          { label: "Total", value: batch.row_count ?? 0 },
          { label: "Pending", value: batch.pending_count ?? 0, color: "var(--status-pending)" },
          { label: "Suspicious", value: batch.suspicious_count ?? 0, color: "var(--status-suspicious)" },
          { label: "Approved", value: batch.approved_count ?? 0, color: "var(--status-approved)" },
          { label: "Locked", value: batch.locked_count ?? 0, color: "var(--status-locked)" },
        ].map(({ label, value, color }) => (
          <div key={label} className="stat-card" style={{ padding: "12px 16px" }}>
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ fontSize: 20, color: color || "var(--text-primary)" }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Layout: table + detail panel */}
      <div className={`batch-detail-grid${selectedRecord ? " has-detail" : ""}`}>
        {/* Record Table */}
        <div className="card" style={{ padding: 0 }}>
          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-2" style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginRight: 8 }}>
              Records
            </span>
            {["", "pending", "suspicious", "approved", "locked", "rejected"].map((s) => (
              <button
                key={s}
                className={`btn ${statusFilter === s ? "btn-primary" : "btn-ghost"}`}
                style={{ padding: "4px 10px", fontSize: 11 }}
                onClick={() => { setStatusFilter(s); setSelectedRecord(null); }}
              >
                {s || "All"}
              </button>
            ))}
          </div>

          {recordsLoading ? (
            <div className="loading-state"><div className="spinner" /></div>
          ) : records.length === 0 ? (
            <div className="empty-state">No records match this filter.</div>
          ) : (
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Status</th>
                    <th>Key Fields</th>
                    <th>CO₂e (kg)</th>
                    <th>Issues</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((rec) => (
                    <tr
                      key={rec.id}
                      onClick={() => setSelectedRecord(rec)}
                      style={{
                        cursor: "pointer",
                        background: selectedRecord?.id === rec.id ? "var(--bg-hover)" : undefined,
                      }}
                    >
                      <td className="monospace" style={{ color: "var(--text-muted)" }}>
                        {rec.row_index + 1}
                      </td>
                      <td><StatusBadge status={rec.status} /></td>
                      <td style={{ maxWidth: 250 }}>
                        <div className="truncate monospace" style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {Object.entries(rec.raw_data)
                            .filter(([, v]) => v)
                            .slice(0, 3)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(" · ")}
                        </div>
                      </td>
                      <td className="monospace">
                        {rec.co2e_kg != null
                          ? <span style={{ color: "var(--accent)" }}>{parseFloat(rec.co2e_kg).toFixed(2)}</span>
                          : <span style={{ color: "var(--text-muted)" }}>—</span>
                        }
                      </td>
                      <td>
                        {rec.error_count > 0 && (
                          <span className="badge badge-suspicious" style={{ marginRight: 4 }}>
                            {rec.error_count} error{rec.error_count !== 1 ? "s" : ""}
                          </span>
                        )}
                        {rec.issue_count > rec.error_count && (
                          <span className="badge badge-warning">
                            {rec.issue_count - rec.error_count} warn
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selectedRecord && (
          <div>
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="flex items-center justify-between mb-4">
                <h2>Row {selectedRecord.row_index + 1}</h2>
                <button
                  className="btn btn-ghost"
                  style={{ padding: "2px 8px", fontSize: 12 }}
                  onClick={() => setSelectedRecord(null)}
                >
                  ✕
                </button>
              </div>

              {/* Raw data preview */}
              <details style={{ marginBottom: 12 }}>
                <summary style={{ cursor: "pointer", fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>
                  Raw CSV Data
                </summary>
                <div style={{
                  background: "var(--bg-secondary)",
                  borderRadius: "var(--radius)",
                  padding: 10,
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-secondary)",
                  overflow: "auto",
                  maxHeight: 200,
                }}>
                  {Object.entries(selectedRecord.raw_data).map(([k, v]) => (
                    <div key={k}>
                      <span style={{ color: "var(--text-muted)" }}>{k}</span>:{" "}
                      <span style={{ color: v ? "var(--text-primary)" : "var(--status-suspicious)" }}>
                        {v || "(empty)"}
                      </span>
                    </div>
                  ))}
                </div>
              </details>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: 16 }}>Validation & Review</h2>
              <IssuePanel
                record={selectedRecord}
                onStatusChange={() => {
                  refetchRecords();
                  queryClient.invalidateQueries(["batch", id]);
                  setSelectedRecord(null);
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Lock batch section */}
      <div className="card mt-4">
        <h2 style={{ marginBottom: 12 }}>Lock Batch for Audit</h2>
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>
          Lock all approved records in this batch. Locked records are immutable and will appear in the audit export.
          This action cannot be undone.
        </p>
        {lockError && <div className="alert alert-error">{lockError}</div>}
        {lockSuccess && <div className="alert alert-success">{lockSuccess}</div>}
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={analystName}
            onChange={(e) => setAnalystName(e.target.value)}
            placeholder="Your name..."
            style={{ maxWidth: 250 }}
          />
          <button
            className="btn btn-primary"
            onClick={handleLock}
            disabled={locking || batch.approved_count === 0}
          >
            {locking ? "Locking..." : `Lock ${batch.approved_count ?? 0} Approved Records`}
          </button>
        </div>
      </div>
    </div>
  );
}
