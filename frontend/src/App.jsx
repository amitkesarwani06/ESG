import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Sidebar from "./components/layout/Sidebar";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Batches from "./pages/Batches";
import BatchDetail from "./pages/BatchDetail";
import AuditLog from "./pages/AuditLog";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
  },
});

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className={`app-layout${sidebarOpen ? " sidebar-open" : ""}`}>
          {/* Sidebar background overlay on mobile */}
          <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
          
          <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          
          <div className="main-content">
            {/* Top mobile navigation navbar */}
            <header className="mobile-header">
              <button className="menu-toggle" aria-label="Toggle Menu" onClick={() => setSidebarOpen(true)}>
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                  <line x1="4" y1="6" x2="20" y2="6"/>
                  <line x1="4" y1="12" x2="20" y2="12"/>
                  <line x1="4" y1="18" x2="20" y2="18"/>
                </svg>
              </button>
              <div className="mobile-logo-text">Breathe ESG</div>
              <div style={{ width: 36 }} /> {/* Balance spacer */}
            </header>

            <div className="page-body">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/batches" element={<Batches />} />
                <Route path="/batches/:id" element={<BatchDetail />} />
                <Route path="/audit-log" element={<AuditLog />} />
              </Routes>
            </div>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
