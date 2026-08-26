import { data } from "react-router-dom";
import { apiClient } from "./client";

export interface JobApplication {
  id: string;
  company_name: string;
  job_title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface JobListResponse {
  items: JobApplication[];
  total: number;
  limit: number;
  offset: number;
}

export const getJobApplications = async (): Promise<JobApplication[]> => {
  const response = await apiClient.get<JobListResponse>("/jobs/")
  return response.data.items;
};

export const createJobApplication = async (data: Partial<JobApplication>): Promise<JobApplication> => {
  const response = await apiClient.post<JobApplication>("/jobs/", data)
  return response.data;
};

export const updateJobApplication = async (id: string, data: Partial<JobApplication>): Promise<JobApplication> => {
  const response = await apiClient.put<JobApplication>(`/jobs/${id}/`, data)
  return response.data;
}

export const deleteJobApplication = async (id: string): Promise<void> => {
  await apiClient.delete(`/jobs/${id}/`);
} 

export const getJobApplicationById = async (id: string): Promise<JobApplication> => {
  const response = await apiClient.get<JobApplication>(`/jobs/${id}/`);
  return response.data;
} 

export const getJobApplicationsByStatus = async (id: string): Promise<JobApplication[]> => {
  const response = await apiClient.get<JobListResponse>(`/jobs/${id}/generate-cober-letter/`, { data });
  return response.data.items;
}