import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MatchScoreDetail } from '../components/MatchScoreDetail';
import * as MatchScoreAPI from '../api/match-score';
import { getJobApplications } from '../api/jobs';
import { type MatchScoreResponse } from '../types/match-score';
import { type JobResponse } from '../types/job';

import {
  Target,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  AlertTriangle,
  Search,
  Building2,
  Calendar
} from 'lucide-react';

const MatchScorePage: React.FC = () => {
  const { jobId } = useParams<{ jobId?: string }>();
  const navigate = useNavigate();

  // Path B's list is just the candidate's tracked jobs - `JobResponse`, the same
  // shape JobList.tsx renders - not a bespoke shape. Its `id` is what Path A
  // (/jobs/:jobId/match-score) needs to fetch a breakdown for one job.
  const [applications, setApplications] = useState<JobResponse[]>([]);
  const [matchScoreData, setMatchScoreData] = useState<MatchScoreResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchApplicantJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJobApplications();
      setApplications(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load applicant jobs';
      console.error(msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSingleMatchScore = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data: MatchScoreResponse = await MatchScoreAPI.getMatchScore(id);
      setMatchScoreData(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error fetching match score';
      console.error(msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (jobId) {
      fetchSingleMatchScore(jobId);
    } else {
      fetchApplicantJobs();
    }
  }, [jobId, fetchApplicantJobs, fetchSingleMatchScore]);

  // Direct rendering for Path A: /jobs/:jobId/match-score
  if (jobId) {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-500 space-y-2">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium">Calculating ATS match breakdown...</p>
        </div>
      );
    }

    if (error || !matchScoreData) {
      return (
        <div className="max-w-2xl mx-auto my-12 p-6 bg-white border border-rose-200 rounded-xl text-center space-y-3">
          <AlertTriangle className="w-10 h-10 mx-auto text-rose-500" />
          <h2 className="text-lg font-bold text-slate-900">Failed to load match score</h2>
          <p className="text-sm text-slate-600">{error || 'Job application data not found.'}</p>
          <button
            onClick={() => navigate('/match-score')}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition-colors"
          >
            Back to All Match Scores
          </button>
        </div>
      );
    }

    // Pass fetched data as a prop to MatchScoreDetail
    return <MatchScoreDetail data={matchScoreData} />;
  }

  // Path B: /match-score (Sidebar / Overview List)
  const filteredJobs = applications.filter((job) =>
    job.job_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.company_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getScoreBadgeColor = (score: number | null) => {
    if (score === null) return 'bg-slate-50 text-slate-500 border-slate-200';
    if (score >= 85) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (score >= 65) return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-rose-50 text-rose-700 border-rose-200';
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6 text-slate-800">

      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Target className="w-6 h-6 text-blue-600" /> Candidate Job Match Scores
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Review ATS match evaluations across all active job applications.
          </p>
        </div>

        {/* Quick Search Bar */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Filter jobs or companies..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>
      </header>

      {/* Main Content Area */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] text-slate-500 space-y-2">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Fetching applicant applications...</p>
        </div>
      ) : error ? (
        <div className="bg-white border border-rose-200 rounded-xl p-12 text-center text-rose-600 space-y-3">
          <AlertTriangle className="w-10 h-10 mx-auto" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 space-y-3">
          <Briefcase className="w-10 h-10 mx-auto text-slate-400" />
          <p className="text-base font-semibold text-slate-700">No job match scores found</p>
          <p className="text-xs">Try adjusting your search query or add a new job to your tracker.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredJobs.map((job) => (
            <article
              key={job.id}
              onClick={() => navigate(`/jobs/${job.id}/match-score`)}
              className="bg-white border border-slate-200 hover:border-blue-400 rounded-xl p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 group"
            >
              {/* Job Info */}
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-lg font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                    {job.job_title}
                  </h2>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
                    {job.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                  <span className="flex items-center gap-1 font-medium text-slate-700">
                    <Building2 className="w-3.5 h-3.5 text-slate-400" /> {job.company_name}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" /> Added: {new Date(job.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Match Score Display & Navigation */}
              <div className="flex items-center justify-between md:justify-end gap-6 border-t md:border-t-0 pt-3 md:pt-0 border-slate-100">
                <div className="text-right">
                  <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border font-bold text-sm ${getScoreBadgeColor(job.match_score)}`}>
                    {job.match_score === null ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : job.match_score >= 80 ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <AlertTriangle className="w-4 h-4" />
                    )}
                    <span>{job.match_score !== null ? `${job.match_score}% Match` : 'Not scored'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all">
                  <span className="text-xs font-semibold hidden sm:inline">Inspect Score</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default MatchScorePage;
