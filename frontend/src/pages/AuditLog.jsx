import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getAuditLog } from "../api/records";

const ACTION_COLOR = {
  status_changed: "#10B981",
  batch_ingested: "#3B82F6",
  batch_uploaded: "#6366F1",
  record_locked: "#8B5CF6",
  record_approved: "#10B981",
  record_rejected: "#EF4444",
};

export default function AuditLogPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-log"],
    queryFn: () => getAuditLog(),
    refetchInterval: 30000,
  });

  const logs = data?.results || data || [];

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span style={{ color: "var(--color-text-muted)", fontSize: 13 }}>Loading audit log…</span>
      </div>
    );
  }

  if (error) return <div className="alert alert-error">Failed to load audit log.</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Log</h1>
          <p className="page-desc">Immutable record of all state changes — {logs.length} entries</p>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {logs.length === 0 ? (
          <div className="empty-state">
            <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{ opacity: 0.25 }}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span style={{ fontSize: 13 }}>No audit events yet.</span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Entity</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <span className="font-mono" style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                      {new Date(log.occurred_at).toLocaleString("en-IN")}
                    </span>
                  </td>
                  <td>
                    <span style={{
                      fontSize: 11, fontFamily: "var(--font-mono)",
                      color: "var(--color-text-secondary)",
                      background: "rgba(255,255,255,0.04)",
                      padding: "2px 6px", borderRadius: 4,
                    }}>
                      {log.entity_type}
                    </span>
                    <div style={{ fontSize: 10, color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", marginTop: 3 }}>
                      {String(log.entity_id).slice(0, 8)}…
                    </div>
                  </td>
                  <td>
                    <code style={{
                      fontSize: 11,
                      background: "rgba(16,185,129,0.08)",
                      padding: "2px 7px",
                      borderRadius: 4,
                      color: ACTION_COLOR[log.action] || "var(--color-accent)",
                      fontFamily: "var(--font-mono)",
                    }}>
                      {log.action}
                    </code>
                  </td>
                  <td style={{ fontSize: 12.5, color: "var(--color-text-secondary)" }}>
                    {log.actor || "—"}
                  </td>
                  <td style={{ fontSize: 11 }}>
                    {log.old_value && log.new_value ? (
                      <span>
                        <span style={{ color: "#EF4444", fontFamily: "var(--font-mono)" }}>{JSON.stringify(log.old_value)}</span>
                        <span style={{ color: "var(--color-text-muted)", margin: "0 4px" }}>→</span>
                        <span style={{ color: "#10B981", fontFamily: "var(--font-mono)" }}>{JSON.stringify(log.new_value)}</span>
                      </span>
                    ) : (
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                        {JSON.stringify(log.new_value || log.old_value)}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
