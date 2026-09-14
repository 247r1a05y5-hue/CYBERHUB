import axios from "axios";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");

export const getApiUrl = (path: string): string => {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath;
};

export const api = axios.create({
  baseURL: API_BASE_URL ? `${API_BASE_URL}/api/v1` : "/api/v1",
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cyberhub_token");
  if (token && !token.startsWith("local_")) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Let the browser set the proper multipart/form-data boundary for FormData payloads
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only clear storage on 401 if it's NOT a login/register request
    if (
      error.response?.status === 401 &&
      !error.config?.url?.includes("/auth/login") &&
      !error.config?.url?.includes("/auth/register")
    ) {
      localStorage.removeItem("cyberhub_token");
      localStorage.removeItem("cyberhub_user");
    }
    return Promise.reject(error);
  }
);
