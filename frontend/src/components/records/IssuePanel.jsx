import React, { useState } from "react";
import { approveRecord, rejectRecord } from "../../api/records";

/**
 * Displays validation issues for a record and provides
 * approve/reject actions for the analyst.
 */
export default function IssuePanel({ record, onStatusChange }) {
  const [analystName, setAnalystName] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const issues = record?.issues || [];
  const status = record?.status;
  const isActionable = status === "pending" || status === "suspicious";

  const handleAction = async (action) => {
    if (!analystName.trim()) {
      setError("Please enter your name before approving or rejecting.");
      return;
    }
    setLoading(action);
    setError("");
    setSuccess("");
    try {
      const fn = action === "approve" ? approveRecord : rejectRecord;
      await fn(record.id, analystName.trim(), note);
      setSuccess(`Record ${action === "approve" ? "approved" : "rejected"} successfully.`);
      onStatusChange?.();
    } catch (err) {
      setError(err.userMessage || `Failed to ${action} record.`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div>
      {/* Issues */}
      {issues.length > 0 ? (
        <ul className="issue-list" style={{ marginBottom: 16 }}>
          {issues.map((issue) => (
            <li key={issue.id} className={`issue-item ${issue.severity}`}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 3 }}>
                  <span className={`badge badge-${issue.severity}`}>{issue.severity}</span>
                  <span className="issue-code">{issue.issue_code}</span>
                  {issue.field_name && (
                    <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                      → {issue.field_name}
                    </span>
                  )}
                </div>
                <div style={{ color: "var(--text-secondary)", fontSize: 12 }}>
                  {issue.message}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 16 }}>
          No validation issues found for this record.
        </p>
      )}

      {/* Analyst Action Panel */}
      {isActionable && (
        <div className="card" style={{ padding: 16 }}>
          <h3 style={{ marginBottom: 12 }}>Analyst Decision</h3>

          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}

          <div className="form-group">
            <label>Your Name *</label>
            <input
              type="text"
              value={analystName}
              onChange={(e) => setAnalystName(e.target.value)}
              placeholder="e.g., Jane Smith"
              disabled={!!loading}
            />
          </div>
          <div className="form-group">
            <label>Note (optional)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Reason for approval or rejection..."
              rows={2}
              disabled={!!loading}
              style={{ resize: "vertical" }}
            />
          </div>

          <div className="flex gap-2">
            <button
              className="btn btn-approve"
              onClick={() => handleAction("approve")}
              disabled={!!loading}
            >
              {loading === "approve" ? "Approving..." : "✓ Approve"}
            </button>
            <button
              className="btn btn-danger"
              onClick={() => handleAction("reject")}
              disabled={!!loading}
            >
              {loading === "reject" ? "Rejecting..." : "✗ Reject"}
            </button>
          </div>
        </div>
      )}

      {status === "locked" && (
        <div className="alert alert-success">
          This record is LOCKED and is part of the audit submission.
        </div>
      )}

      {status === "rejected" && (
        <div className="alert alert-error">
          This record has been rejected and will not appear in the audit export.
        </div>
      )}
    </div>
  );
}
