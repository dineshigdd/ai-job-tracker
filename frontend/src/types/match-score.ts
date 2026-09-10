// types/match-score.ts

/**
 * Body of POST /jobs/{job_id}/match-score
 */
export interface MatchScoreRequest {
  /** Resume to score against. Defaults to the user's active resume. */
  resume_id?: string;
}

/**
 * Base type for one weighted component of the match score.
 * An unavailable component has `score: null`, is excluded from weighted averages,
 * and carries a `reason` the UI should render instead of a number.
 */
export interface MatchScoreComponent {
  score: number | null;
  available: boolean;
  reason: string | null;
}

/**
 * Hard or Soft skill breakdown component.
 */
export interface SkillMatchComponent extends MatchScoreComponent {
  matched_skills: string[];
  missing_skills: string[];
}

/**
 * Experience matching breakdown component.
 */
export interface ExperienceMatchComponent extends MatchScoreComponent {
  user_experience: string;
  required_experience: string;
}

/**
 * Detailed breakdown block containing all components.
 */
export interface MatchScoreBreakdown {
  hard_skills: SkillMatchComponent;
  soft_skills: SkillMatchComponent;
  experience: ExperienceMatchComponent;
  keyword_density: MatchScoreComponent;
}

/**
 * Full backend response model for GET/POST match score calls.
 */
export interface MatchScoreResponse {
  job_id: string; // UUID
  match_score: number | null; // Null when no component could be evaluated
  interpretation: string;
  breakdown: MatchScoreBreakdown;
  suggestions: string[];
  notes: string[];
  resume_id: string; // UUID
  resume_filename: string;
  resume_version: string;
  algorithm_version: string;
  calculated_at: string; // ISO Datetime string
}