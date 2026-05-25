import client from "./client";

export const getBatches = () => client.get("/batches/").then((r) => r.data);
export const getBatch = (id) => client.get(`/batches/${id}/`).then((r) => r.data);
export const getStats = () => client.get("/stats/").then((r) => r.data);
export const getSourceTypes = () => client.get("/source-types/").then((r) => r.data);

export const uploadBatch = (formData) =>
  client.post("/batches/upload/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);

export const lockBatch = (batchId, analystName) =>
  client.post(`/batches/${batchId}/lock/`, { analyst_name: analystName }).then((r) => r.data);
