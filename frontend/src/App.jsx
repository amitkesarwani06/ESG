import React from "react";
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
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-layout">
          <Sidebar />
          <div className="main-content">
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
