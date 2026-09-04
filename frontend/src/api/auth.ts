// src/api/auth.ts
//
// There is no token handling anywhere in this file by design. The session lives
// entirely in the backend's HttpOnly cookie, which this code cannot read, store
// or forward — the browser attaches it automatically because `withCredentials`
// is set and the API is same-origin (see ./client.ts).
import { apiClient } from "./client";
import type { User } from "../types/auth";

// POST /auth/login returns the user's profile; the JWT arrives as a Set-Cookie
// header and never passes through JavaScript.
export const loginUser = async (email: string, password: string): Promise<User> => {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await apiClient.post<User>("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });
  return response.data;
};

export const logoutUser = async (): Promise<void> => {
  await apiClient.post("/auth/logout");
};

export const fetchCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>("/users/me");
  return response.data;
};
