import React from "react";

const STATUS_CONFIG = {
  pending:    { label: "Pending",    cls: "badge-pending",    dot: "#F59E0B" },
  suspicious: { label: "Suspicious", cls: "badge-suspicious", dot: "#EF4444" },
  approved:   { label: "Approved",   cls: "badge-approved",   dot: "#10B981" },
  locked:     { label: "Locked",     cls: "badge-locked",     dot: "#6366F1" },
  rejected:   { label: "Rejected",   cls: "badge-rejected",   dot: "#6B7280" },
  processing: { label: "Processing", cls: "badge-pending",    dot: "#F59E0B" },
  completed:  { label: "Completed",  cls: "badge-approved",   dot: "#10B981" },
  failed:     { label: "Failed",     cls: "badge-suspicious", dot: "#EF4444" },
};

export default function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: status, cls: "badge-pending", dot: "#94A3B8" };
  return (
    <span className={`badge ${cfg.cls}`}>
      <span className="badge-dot" style={{ background: cfg.dot }} />
      {cfg.label}
    </span>
  );
}
