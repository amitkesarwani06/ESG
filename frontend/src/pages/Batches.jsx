import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getBatches } from "../api/batches";
import StatusBadge from "../components/records/StatusBadge";

export default function Batches() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["batches"],
    queryFn: getBatches,
    refetchInterval: 15000,
  });

  const batches = data?.results || data || [];

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span style={{ color: "var(--color-text-muted)", fontSize: 13 }}>Loading batches…</span>
      </div>
    );
  }

  if (error) {
    return <div className="alert alert-error">Failed to load batches: {error.message}</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Upload Batches</h1>
          <p className="page-desc">{batches.length} batch{batches.length !== 1 ? "es" : ""} total</p>
        </div>
        <Link to="/upload" className="btn btn-primary">
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Upload
        </Link>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {batches.length === 0 ? (
          <div className="empty-state">
            <svg width="36" height="36" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{ opacity: 0.25 }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <div style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-secondary)" }}>No batches yet</div>
            <Link to="/upload" className="btn btn-primary btn-sm" style={{ marginTop: 4 }}>Upload your first file</Link>
          </div>
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Source Type</th>
                  <th>Uploaded By</th>
                  <th>Date</th>
                  <th>Rows</th>
                  <th>Pending</th>
                  <th>Suspicious</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.id}>
                    <td style={{ maxWidth: 220 }}>
                      <div className="font-mono truncate" style={{ color: "var(--color-text-primary)", fontSize: 12 }} title={batch.filename}>
                        {batch.filename}
                      </div>
                    </td>
                    <td>
                      {batch.source_type && (
                        <span className={`scope-badge scope-${batch.source_type.scope}`}>
                          S{batch.source_type.scope} · {batch.source_type.code}
                        </span>
                      )}
                    </td>
                    <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{batch.uploaded_by}</td>
                    <td>
                      <span style={{ fontSize: 12, color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
                        {new Date(batch.uploaded_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                      </span>
                    </td>
                    <td className="font-mono" style={{ color: "var(--color-text-primary)" }}>{batch.row_count ?? "—"}</td>
                    <td>
                      {batch.pending_count > 0 && (
                        <span className="badge badge-pending">{batch.pending_count}</span>
                      )}
                    </td>
                    <td>
                      {batch.suspicious_count > 0 && (
                        <span className="badge badge-suspicious">{batch.suspicious_count}</span>
                      )}
                    </td>
                    <td><StatusBadge status={batch.status} /></td>
                    <td>
                      <Link to={`/batches/${batch.id}`} className="btn btn-ghost btn-sm">Review →</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
