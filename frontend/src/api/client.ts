import axios from "axios";

// Deliberately a RELATIVE path by default. The app is served from the same
// origin as the API in every environment — Vite proxies /api to 127.0.0.1:8000
// in development (vite.config.ts) and Vercel rewrites /api to the Render
// service in production (vercel.json). That keeps the backend's auth cookie
// first-party, which is the only way an HttpOnly cookie can be used at all:
// a cross-origin API URL would make it a third-party cookie, which browsers
// either refuse to send (SameSite=Lax) or block outright (Safari, Brave).
//
// Only override VITE_API_URL to talk to a backend that is genuinely on the
// same site (e.g. https://api.example.com from https://app.example.com).
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  // Render's free tier cold-starts, and the AI endpoints call out to Groq;
  // 10s produced spurious failures on the first request after an idle period.
  timeout: 60000,
  // Sends the HttpOnly auth cookie. Required even same-origin for the
  // cross-origin case in local development (localhost:3000 -> the proxy).
  withCredentials: true,
});

// Interceptor to handle global error responses (e.g., redirect on 401 Unauthorized)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? "";
    const isMeEndpoint = url.includes("/users/me");
    const isAuthEndpoint = url.includes("/auth/");

    // Don't force a redirect if the 401 came from a session check or a login
    // attempt: those callers handle it themselves.
    if (
      error.response?.status === 401 &&
      !isMeEndpoint &&
      !isAuthEndpoint
    ) {
      window.location.href = "/users/login";
    }

    return Promise.reject(error);
  }
);
