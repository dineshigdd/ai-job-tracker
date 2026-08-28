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