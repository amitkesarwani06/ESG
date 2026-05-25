import React, { useState } from "react";
import { uploadBatch } from "../../api/batches";

const STEPS = [
  "CSV is parsed and each row stored as a raw record (immutable)",
  "Validation engine checks for errors and warnings per row",
  "Normalization converts units, dates, and codes to canonical forms",
  "CO₂e is calculated using published emission factors (UK DESNZ 2023)",
  "Analyst reviews and approves / rejects suspicious rows",
  "Approved rows are locked for audit submission",
];

export default function UploadZone({ sourceTypes, onSuccess }) {
  const types = Array.isArray(sourceTypes) ? sourceTypes : (sourceTypes?.results || []);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [sourceTypeCode, setSourceTypeCode] = useState("");
  const [clientSlug, setClientSlug] = useState("demo-client");
  const [analystName, setAnalystName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.endsWith(".csv")) { setFile(f); setError(""); }
    else setError("Only CSV files are accepted.");
  };

  const handleFileInput = (e) => {
    const f = e.target.files[0];
    if (f) { setFile(f); setError(""); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return setError("Please select a CSV file.");
    if (!sourceTypeCode) return setError("Please select a source type.");
    if (!analystName.trim()) return setError("Please enter your name.");

    const fd = new FormData();
    fd.append("file", file);
    fd.append("source_type_code", sourceTypeCode);
    fd.append("client_slug", clientSlug || "demo-client");
    fd.append("uploaded_by", analystName.trim());

    setLoading(true); setError(""); setResult(null);
    try {
      const data = await uploadBatch(fd);
      setResult(data); onSuccess?.(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.userMessage || "Upload failed. Is the backend running?");
    } finally { setLoading(false); }
  };

  if (result) {
    return (
      <div>
        <div className="alert alert-success" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          Upload complete — {result.stats?.total_rows} rows ingested
          {result.stats?.suspicious_rows > 0 && `, ${result.stats.suspicious_rows} suspicious detected`}.
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: "var(--color-text-primary)" }}>Ingestion Summary</h2>
          <div className="stat-grid" style={{ gridTemplateColumns: "repeat(3,1fr)" }}>
            <MiniStat label="Total Rows"  value={result.stats?.total_rows ?? 0} />
            <MiniStat label="Pending"     value={result.stats?.pending_rows ?? 0}    color="#F59E0B" />
            <MiniStat label="Suspicious"  value={result.stats?.suspicious_rows ?? 0} color="#EF4444" />
          </div>
          <button className="btn btn-primary" onClick={() => { setResult(null); setFile(null); }}>
            Upload Another File
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="alert alert-error">{error}</div>}

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("csv-file-input").click()}
        style={{
          border: `2px dashed ${dragging ? "var(--color-accent)" : "var(--color-border)"}`,
          borderRadius: 12,
          padding: "36px 24px",
          textAlign: "center",
          cursor: "pointer",
          background: dragging ? "var(--color-accent-dim)" : "rgba(255,255,255,0.01)",
          transition: "all 0.2s",
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 10, lineHeight: 1 }}>
          {file ? "📄" : "📁"}
        </div>
        {file ? (
          <div>
            <div style={{ fontWeight: 600, color: "var(--color-text-primary)", fontSize: 14 }}>{file.name}</div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>
              {(file.size / 1024).toFixed(1)} KB · Click to change
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontWeight: 500, color: "var(--color-text-secondary)", fontSize: 14 }}>
              Drop a CSV file here, or click to browse
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>
              CSV only · Max 10 MB
            </div>
          </div>
        )}
        <input id="csv-file-input" type="file" accept=".csv" onChange={handleFileInput} style={{ display: "none" }} />
      </div>

      <div className="form-group">
        <label>Source Type *</label>
        <select value={sourceTypeCode} onChange={(e) => setSourceTypeCode(e.target.value)} required>
          <option value="">Select source type...</option>
          {types.map((st) => (
            <option key={st.code} value={st.code}>S{st.scope} · {st.label}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Client Slug</label>
        <input type="text" value={clientSlug} onChange={(e) => setClientSlug(e.target.value)} placeholder="demo-client" />
        <div className="form-hint">Used to identify which client this data belongs to</div>
      </div>

      <div className="form-group">
        <label>Uploaded By *</label>
        <input type="text" value={analystName} onChange={(e) => setAnalystName(e.target.value)} placeholder="Your name or email" required />
      </div>

      <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading || !file}>
        {loading ? (
          <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginRight: 6 }} />Processing…</>
        ) : "Upload & Ingest"}
      </button>
    </form>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ fontSize: 24, color: color || "var(--color-text-primary)" }}>{value}</div>
    </div>
  );
}
