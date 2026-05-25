import client from "./client";

export const getBatchRecords = (batchId, params = {}) =>
  client.get(`/batches/${batchId}/records/`, { params }).then((r) => r.data);

export const getRecord = (id) =>
  client.get(`/records/${id}/`).then((r) => r.data);

export const approveRecord = (id, analystName, note = "") =>
  client
    .post(`/records/${id}/approve/`, { analyst_name: analystName, note })
    .then((r) => r.data);

export const rejectRecord = (id, analystName, note = "") =>
  client
    .post(`/records/${id}/reject/`, { analyst_name: analystName, note })
    .then((r) => r.data);

export const getAuditLog = (params = {}) =>
  client.get("/audit-log/", { params }).then((r) => r.data);
