import { apiClient } from "./client";

// --- INTERFACES ---

export interface ResumeSummary {
  id: string;
  user_id: string;
  filename: string;
  content_hash: string;
  is_active: boolean;
  extracted_text_length: number;
  created_at: string;
}

export interface ResumeDetail extends ResumeSummary {
  extracted_text: string;
}

export interface KeyFinding {
  text: string;
  matched: boolean;
}

export interface ResumeAnalysisResponse {
  filename: string;
  extracted_text_length: number;
  ai_feedback: string;
  resume: ResumeSummary;
  // Parsed fields on the frontend for rendering UI gauges & feedback lists
  match_score?: number;
  assessment?: string;
  key_findings?: KeyFinding[];
  suggestions?: string[];
}

// --- API FUNCTIONS ---

// GET /resumes/
export const getResumeList = async (): Promise<ResumeSummary[]> => {
  const response = await apiClient.get<ResumeSummary[]>("/resumes/");
  return response.data;
};

// GET /resumes/active
export const getActiveResume = async (): Promise<ResumeDetail> => {
  const response = await apiClient.get<ResumeDetail>("/resumes/active");
  return response.data;
};

// GET /resumes/{id}
export const getResume = async (id: string): Promise<ResumeDetail> => {
  const response = await apiClient.get<ResumeDetail>(`/resumes/${id}`);
  return response.data;
};

// POST /resumes/analyze
export const uploadAndAnalyzeResume = async (
  file: File,
  jobDescription?: string
): Promise<ResumeAnalysisResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  if (jobDescription && jobDescription.trim() !== "") {
    formData.append("job_description", jobDescription.trim());
  }

  const response = await apiClient.post<ResumeAnalysisResponse>(
    "/resumes/analyze",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );
  return response.data;
};

// POST /resumes/{id}/analyze
export const analyzeResumeById = async (
  id: string,
  jobDescription?: string
): Promise<ResumeAnalysisResponse> => {
  // Body(None, embed=True) expects { "job_description": "..." }
  const payload = jobDescription && jobDescription.trim() !== "" 
    ? { job_description: jobDescription.trim() } 
    : {};

  const response = await apiClient.post<ResumeAnalysisResponse>(
    `/resumes/${id}/analyze`,
    payload
  );
  return response.data;
};

// PUT /resumes/{id}/activate
export const makeResumeActive = async (id: string): Promise<ResumeSummary> => {
  const response = await apiClient.put<ResumeSummary>(`/resumes/${id}/activate`);
  return response.data;
};

// DELETE /resumes/{id}
export const deleteResume = async (id: string): Promise<void> => {
  await apiClient.delete(`/resumes/${id}`);
};