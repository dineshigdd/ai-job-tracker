// src/api/user.ts
import axios from "axios";
import { type User } from "../types/auth";



// GET /users/me
export const getCurrentUserProfile = async (): Promise<User> => {
  const response = await axios.get(`/users/me`);
  return response.data;
};

// PUT /users/me
export const updateUserProfile = async (data: Partial<User> & { password?: string }): Promise<User> => {
  const response = await axios.put(`/users/me`, data);
  return response.data;
};

// DELETE /users/me
export const deleteUserAccount = async (): Promise<void> => {
  await axios.delete(`/users/me`);
};