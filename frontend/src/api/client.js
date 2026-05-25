import axios from "axios";

/**
 * Axios instance pre-configured for the ESG backend.
 * VITE_API_BASE_URL is set per-environment:
 *   - dev: http://localhost:8000/api
 *   - prod: https://esg-backend.onrender.com/api
 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: could add auth token here in production
client.interceptors.request.use((config) => {
  return config;
});

// Response interceptor: normalize error structure
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail || error.message;
    error.userMessage = detail;
    return Promise.reject(error);
  }
);

export default client;
