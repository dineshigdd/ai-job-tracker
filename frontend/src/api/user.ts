import { apiClient } from "./client";
import { type User } from "../types/auth";

export interface RegisterPayload {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}

// Separate payload interface for updates (makes optional fields explicit)
export interface UpdateUserPayload {
  first_name?: string;
  last_name?: string;
  email?: string;
  password?: string;
}

// POST /users/register
export const registerUser = async (data: RegisterPayload): Promise<User> => {
  const response = await apiClient.post<User>("/users/register", data);
  return response.data;
};

// GET /users/me
export const getCurrentUserProfile = async (): Promise<User> => {
  const response = await apiClient.get<User>(`/users/me`);
  return response.data;
};

// PUT /users/me
export const updateUserProfile = async (data: UpdateUserPayload): Promise<User> => {
  const response = await apiClient.put<User>(`/users/me`, data);
  return response.data;
};

// DELETE /users/me
export const deleteUserAccount = async (): Promise<void> => {
  await apiClient.delete(`/users/me`);
};