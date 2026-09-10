// api/match-score.ts
import { apiClient } from "./client";
import { type MatchScoreRequest, type MatchScoreResponse } from '../types/match-score';

/**
 * Fetch the calculated match score for a job application
 */

export const getMatchScore = async (jobId: string): Promise<MatchScoreResponse> => {
  const response = await apiClient.get<MatchScoreResponse>(`/jobs/${jobId}/match-score`);
  return response.data;
}

/**
 * Post or trigger recalculation of a match score against a specific resume
 */


export const calculateMatchScore = async (
  jobId: string, 
  payload: MatchScoreRequest = {}): Promise<MatchScoreResponse> => {
  const response = await apiClient.post<MatchScoreResponse>(`/jobs/${jobId}/match-score`, payload);
  return response.data;
}   