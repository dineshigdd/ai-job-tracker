import { apiClient } from "./client";

// --- ENUMS & TYPES ---

export type JobStatus = 
  | "Wishlist" 
  | "Applied" 
  | "Interviewing" 
  | "Offer" 
  | "Rejected";

export const STATUS_ORDER: JobStatus[] = [
  "Wishlist",
  "Applied",
  "Interviewing",
  "Offer",
  "Rejected",
];

export type JobSort = "newest" | "oldest" | "company" | "score_desc";

// --- INTERFACES MATCHING PYDANTIC SCHEMAS ---

// Matches Python `JobStatusEventResponse`
export interface JobStatusEventResponse {
  id: string; // UUID string
  job_id: string; // UUID string
  from_status: string | null;
  to_status: string;
  changed_at: string; // ISO DateTime string
}

// Matches Python `JobCreate`
export interface JobCreate {
  company_name: string;
  job_title: string;
  job_description?: string | null;
  status?: JobStatus;
  ai_cover_letter?: string | null;
  match_score?: number | null;
  interview_date?: string | null; // ISO DateTime string
}

// Matches Python `JobUpdate`
export interface JobUpdate {
  company_name?: string | null;
  job_title?: string | null;
  job_description?: string | null;
  status?: JobStatus | null;
  ai_cover_letter?: string | null;
  match_score?: number | null;
  interview_date?: string | null; // ISO DateTime string
}

// Matches Python `JobResponse`
export interface JobResponse {
  id: string; // UUID string
  user_id: string; // UUID string
  company_name: string;
  job_title: string;
  job_description: string | null;
  status: JobStatus;
  ai_cover_letter: string | null;
  match_score: number | null;
  interview_date: string | null; // ISO DateTime string
  cover_letter_generated_at: string | null; // ISO DateTime string
  created_at: string; // ISO DateTime string
  updated_at: string; // ISO DateTime string
  status_events: JobStatusEventResponse[];
}

// Matches Python `JobListResponse` (Paginated envelope for GET /jobs/)
export interface JobListResponse {
  items: JobResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Query parameters for GET /jobs/ matching router filters
export interface GetJobsParams {
  status?: JobStatus;
  search?: string;
  min_score?: number;
  max_score?: number;
  limit?: number;
  offset?: number;
  sort?: JobSort;
}

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