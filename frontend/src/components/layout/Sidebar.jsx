import React from "react";
import { NavLink } from "react-router-dom";
import logoSvg from "../../assets/logo.svg";

const navItems = [
  {
    path: "/",
    label: "Dashboard",
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <rect x="3" y="3" width="7" height="7" rx="1.5"/>
        <rect x="14" y="3" width="7" height="7" rx="1.5"/>
        <rect x="3" y="14" width="7" height="7" rx="1.5"/>
        <rect x="14" y="14" width="7" height="7" rx="1.5"/>
      </svg>
    ),
  },
  {
    path: "/upload",
    label: "Upload Data",
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
    ),
  },
  {
    path: "/batches",
    label: "Batches",
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <line x1="8" y1="6" x2="21" y2="6"/>
        <line x1="8" y1="12" x2="21" y2="12"/>
        <line x1="8" y1="18" x2="21" y2="18"/>
        <line x1="3" y1="6" x2="3.01" y2="6"/>
        <line x1="3" y1="12" x2="3.01" y2="12"/>
        <line x1="3" y1="18" x2="3.01" y2="18"/>
      </svg>
    ),
  },
  {
    path: "/audit-log",
    label: "Audit Log",
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
    ),
  },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <aside className={`sidebar${isOpen ? " open" : ""}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Breathe ESG logo */}
          <div style={{
            width: 36, height: 36,
            background: "var(--color-bg-primary)",
            borderRadius: 9,
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
            border: "1px solid rgba(16,185,129,0.2)",
            padding: 4,
          }}>
            <img src={logoSvg} alt="Breathe ESG" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, letterSpacing: "-0.01em" }} className="gradient-text">
              Breathe ESG
            </div>
            <div style={{ fontSize: 10, color: "var(--color-text-muted)", marginTop: 1 }}>
              Data Platform
            </div>
          </div>
        </div>

        {/* Mobile close button */}
        <button className="sidebar-close-btn" aria-label="Close menu" onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Navigation */}
      <nav style={{ padding: "16px 12px", flex: 1 }}>
        <div className="nav-section-label" style={{ marginBottom: 8 }}>Navigation</div>
        {navItems.map(({ path, label, icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            onClick={onClose}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: "16px 20px", borderTop: "1px solid var(--color-border)" }}>
        <div style={{ fontSize: 10, color: "var(--color-text-muted)", marginBottom: 8, fontWeight: 500 }}>
          GHG Protocol Aligned
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {[1, 2, 3].map((scope) => (
            <span key={scope} className={`scope-badge scope-${scope}`}>S{scope}</span>
          ))}
        </div>
      </div>
    </aside>
  );
}
