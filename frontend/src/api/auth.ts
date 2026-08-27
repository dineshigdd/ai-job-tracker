// src/api/auth.ts
import { apiClient } from "./client";

export interface User {
  id: string;
  email: string;
  // created_at: string; to be added later
}

export const loginUser = async (email: string, password: string): Promise<void> => {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  await apiClient.post("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });
};

export const logoutUser = async (): Promise<void> => {
  await apiClient.post("/auth/logout");
};

export const fetchCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>("/users/me");
  return response.data;
};