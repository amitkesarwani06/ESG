import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getStats } from "../api/batches";
import StatusBadge from "../components/records/StatusBadge";

const STAT_CARDS = [
  { key: "pending", label: "Pending Review", accent: "accent-pending", color: "#F59E0B" },
  { key: "suspicious", label: "Suspicious", accent: "accent-suspicious", color: "#EF4444" },
  { key: "approved", label: "Approved", accent: "accent-approved", color: "#10B981" },
  { key: "locked", label: "Locked", accent: "accent-locked", color: "#6366F1" },
];

const SCOPE_MAP = {
  sap_fuel: { scope: 1, label: "SAP Fuel & Procurement" },
  utility_elec: { scope: 2, label: "Utility Electricity" },
  corporate_travel: { scope: 3, label: "Corporate Travel" },
};

export default function Dashboard() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span style={{ color: "var(--color-text-muted)", fontSize: 13 }}>Loading dashboard…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        Failed to load dashboard: {error.message}
      </div>
    );
  }

  const statusCounts = stats?.status_counts || {};
  const co2eBySource = stats?.co2e_by_source || [];
  const recentBatches = stats?.recent_batches || [];

  const totalCo2eKg = co2eBySource.reduce((s, x) => s + (parseFloat(x.total_co2e_kg) || 0), 0);

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-desc">GHG data ingestion overview — Scope 1, 2 &amp; 3</p>
        </div>
        <Link to="/upload" className="btn btn-primary">
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Upload Data
        </Link>
      </div>

      {/* Status Stat Cards */}
      <div className="stat-grid">
        {STAT_CARDS.map(({ key, label, accent, color }) => (
          <div key={key} className={`stat-card ${accent}`}>
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ color }}>{statusCounts[key] ?? 0}</div>
            <div className="stat-sub">records</div>
          </div>
        ))}
        <div className="stat-card accent-co2">
          <div className="stat-label">Total CO₂e</div>
          <div className="stat-value" style={{ fontSize: 24, color: "var(--color-accent)" }}>
            {(totalCo2eKg / 1000).toFixed(2)}
          </div>
          <div className="stat-sub">tonnes CO₂e</div>
        </div>
      </div>

      {/* CO2e by Source */}
      <div className="card mb-6">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--color-text-primary)" }}>Emissions by Source</h2>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            tCO₂e
          </span>
        </div>

        {co2eBySource.length === 0 ? (
          <div className="empty-state" style={{ padding: "28px 0" }}>
            <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" style={{ opacity: 0.3 }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span style={{ fontSize: 13 }}>No emissions data yet. <Link to="/upload" style={{ color: "var(--color-accent)" }}>Upload a file →</Link></span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {co2eBySource.map((item) => {
              const meta = SCOPE_MAP[item.source_type_code] || { scope: "?", label: item.source_type_code };
              const tonnes = (parseFloat(item.total_co2e_kg) / 1000).toFixed(3);
              const pct = totalCo2eKg > 0 ? (parseFloat(item.total_co2e_kg) / totalCo2eKg) * 100 : 0;
              return (
                <div key={item.source_type_code}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span className={`scope-badge scope-${meta.scope}`}>S{meta.scope}</span>
                    <span style={{ flex: 1, fontSize: 13, color: "var(--color-text-secondary)" }}>{meta.label}</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--color-text-primary)", fontWeight: 600 }}>
                      {tonnes}
                    </span>
                  </div>
                  <div style={{ height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
                    <div style={{
                      height: "100%", width: `${pct}%`,
                      background: meta.scope === 1 ? "#F97316" : meta.scope === 2 ? "#3B82F6" : "#8B5CF6",
                      borderRadius: 2, transition: "width 0.6s ease",
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Batches */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--color-text-primary)" }}>Recent Uploads</h2>
          <Link to="/batches" className="btn btn-ghost btn-sm">View all →</Link>
        </div>

        {recentBatches.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
            No batches yet. <Link to="/upload" style={{ color: "var(--color-accent)" }}>Upload your first file →</Link>
          </p>
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Source</th>
                  <th>Uploaded By</th>
                  <th>Rows</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentBatches.map((batch) => (
                  <tr key={batch.id}>
                    <td style={{ maxWidth: 200 }}>
                      <div className="font-mono truncate" style={{ color: "var(--color-text-primary)", fontSize: 12 }}>
                        {batch.filename}
                      </div>
                      <div className="text-xs text-muted" style={{ marginTop: 2 }}>
                        {new Date(batch.uploaded_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                      </div>
                    </td>
                    <td>
                      {batch.source_type && (
                        <span className={`scope-badge scope-${batch.source_type.scope}`}>
                          S{batch.source_type.scope} · {batch.source_type.label}
                        </span>
                      )}
                    </td>
                    <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{batch.uploaded_by}</td>
                    <td className="font-mono" style={{ color: "var(--color-text-primary)" }}>{batch.row_count ?? "—"}</td>
                    <td><StatusBadge status={batch.status} /></td>
                    <td>
                      <Link to={`/batches/${batch.id}`} className="btn btn-ghost btn-sm">
                        Review →
                      </Link>
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
