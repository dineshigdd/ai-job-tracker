import { apiClient } from "./client";
import type { 
      JobCreate, 
      JobUpdate, 
      JobResponse, 
      JobListResponse, 
      GetJobsParams 
} from "../types/job";


// --- API FUNCTIONS ---

// GET /jobs/ (Fetches paginated response with optional filtering)
export const getJobs = async (params?: GetJobsParams): Promise<JobListResponse> => {
  const response = await apiClient.get<JobListResponse>("/jobs/", { params });
  return response.data;
};

// GET /jobs/ (Shortcut helper to get array of items directly)
export const getJobApplications = async (params?: GetJobsParams): Promise<JobResponse[]> => {
  const response = await apiClient.get<JobListResponse>("/jobs/", { params });
  return response.data.items;
};

// GET /jobs/{job_id}
export const getJobApplicationById = async (id: string): Promise<JobResponse> => {
  const response = await apiClient.get<JobResponse>(`/jobs/${id}`);
  return response.data;
};

// POST /jobs/
export const createJobApplication = async (data: JobCreate): Promise<JobResponse> => {
  const response = await apiClient.post<JobResponse>("/jobs/", data);
  return response.data;
};

// PATCH /jobs/{job_id}
export const updateJobApplication = async (id: string, data: JobUpdate): Promise<JobResponse> => {
  const response = await apiClient.patch<JobResponse>(`/jobs/${id}`, data);
  return response.data;
};

// DELETE /jobs/{job_id}
export const deleteJobApplication = async (id: string): Promise<void> => {
  await apiClient.delete(`/jobs/${id}`);
};

// POST /jobs/{job_id}/generate-cover-letter
export const generateCoverLetter = async (id: string): Promise<JobResponse> => {
  const response = await apiClient.post<JobResponse>(`/jobs/${id}/generate-cover-letter`);
  return response.data;
};