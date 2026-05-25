import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getSourceTypes } from "../api/batches";
import UploadZone from "../components/upload/UploadZone";
import { useNavigate } from "react-router-dom";

const STEPS = [
  { num: "01", text: "CSV parsed — each row stored as a raw record (immutable)" },
  { num: "02", text: "Validation engine flags errors & warnings per row" },
  { num: "03", text: "Normalization converts units, dates, and codes to canonical forms" },
  { num: "04", text: "CO₂e calculated using published emission factors (UK DESNZ 2023)" },
  { num: "05", text: "Analyst reviews and approves / rejects suspicious rows" },
  { num: "06", text: "Approved rows locked — immutable for audit submission" },
];

const SAMPLES = [
  { scope: 1, file: "sap_fuel_export.csv", desc: "SAP MB51 export, German locale, includes intentional bad rows" },
  { scope: 2, file: "utility_electricity.csv", desc: "Multi-portal format, overlapping billing periods" },
  { scope: 3, file: "travel_concur_export.csv", desc: "Concur SAE style, free-text IATA airport codes" },
];

export default function Upload() {
  const navigate = useNavigate();
  const { data: sourceTypes } = useQuery({ queryKey: ["source-types"], queryFn: getSourceTypes });
  const handleSuccess = (data) => { setTimeout(() => navigate(`/batches/${data.batch.id}`), 1500); };

  return (
    <div style={{ maxWidth: 580 }}>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="page-title">Upload Data</h1>
          <p className="page-desc">Upload a CSV from SAP, a utility portal, or a travel platform.</p>
        </div>
      </div>

      {/* How it works */}
      <div className="card mb-6" style={{ borderLeft: "3px solid var(--color-accent)" }}>
        <div className="section-label" style={{ marginBottom: 14 }}>How Ingestion Works</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {STEPS.map(({ num, text }) => (
            <div key={num} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
                color: "var(--color-accent)", background: "var(--color-accent-dim)",
                padding: "2px 6px", borderRadius: 4, flexShrink: 0, marginTop: 1
              }}>{num}</span>
              <span style={{ fontSize: 12.5, color: "var(--color-text-secondary)", lineHeight: 1.6 }}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Upload form */}
      <div className="card mb-4">
        <UploadZone sourceTypes={sourceTypes} onSuccess={handleSuccess} />
      </div>

      {/* Sample files */}
      <div className="card">
        <div className="section-label" style={{ marginBottom: 12 }}>Sample Test Files</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {SAMPLES.map(({ scope, file, desc }) => (
            <div key={file} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span className={`scope-badge scope-${scope}`} style={{ flexShrink: 0, marginTop: 1 }}>S{scope}</span>
              <div>
                <code style={{ fontSize: 12, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>{file}</code>
                <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 2 }}>{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
