import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
  // CRITICAL: This tells Axios to include cookies in cross-origin requests
  withCredentials: true,
});



// Interceptor to handle global error responses (e.g., redirect on 401 Unauthorized)
// ✅ CORRECT
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isMeEndpoint = error.config?.url?.includes("/users/me");
    const isAuthEndpoint = error.config?.url?.includes("/auth/");

    // Don't force redirect if the 401 came from session checks or login attempts
    if (error.response?.status === 401 && !isMeEndpoint && !isAuthEndpoint) {
      window.location.href = "/users/login";
    }

    return Promise.reject(error);
  }
);
