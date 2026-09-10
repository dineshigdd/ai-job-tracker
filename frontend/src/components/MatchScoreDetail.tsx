import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  RotateCw, 
  Download, 
  Briefcase, 
  Cpu, 
  Users, 
  TrendingUp, 
  Sparkles,
  AlertTriangle 
} from 'lucide-react';
import * as MatchScoreAPI from '../api/match-score';
import { type MatchScoreComponent, type MatchScoreResponse } from '../types/match-score';

/**
 * Renders a component's score, or "N/A" plus its `reason` when the backend
 * marked it unavailable (`available: false`, `score: null` — §3.4's
 * no-data-is-not-a-zero rule; see `MatchScoreComponent` in types/match-score.ts).
 */
function formatComponentScore(component: MatchScoreComponent): string {
  return component.score !== null ? `${Math.round(component.score)}%` : 'N/A';
}

interface Props {
  jobId?: string;
  data?: MatchScoreResponse;
  onBack?: () => void;
}

export const MatchScoreDetail: React.FC<Props> = ({ jobId: propJobId, data: propData, onBack }) => {
  const params = useParams<{ jobId?: string }>();
  const activeJobId = params.jobId || propJobId;
  const navigate = useNavigate();

  const [scoreData, setScoreData] = useState<MatchScoreResponse | null>(propData || null);
  const [loading, setLoading] = useState<boolean>(!propData && !!activeJobId);
  const [recalculating, setRecalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sync prop changes into state
  useEffect(() => {
    if (propData) {
      setScoreData(propData);
      setLoading(false);
    }
  }, [propData]);

  const fetchMatchScore = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await MatchScoreAPI.getMatchScore(id);
      setScoreData(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch match score';
      console.error(msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!propData && activeJobId) {
      fetchMatchScore(activeJobId);
    }
  }, [activeJobId, propData, fetchMatchScore]);

  const handleRecalculate = async () => {
    if (!activeJobId) return;
    setRecalculating(true);
    try {
      const updated = await MatchScoreAPI.calculateMatchScore(activeJobId);
      setScoreData(updated);
    } catch (err) {
      console.error('Error recalculating score:', err);
    } finally {
      setRecalculating(false);
    }
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate('/match-score');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-500 space-y-3">
        <RotateCw className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-sm font-medium">Calculating ATS Match Analytics...</p>
      </div>
    );
  }

  if (error || !scoreData) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-6 bg-white border border-rose-200 rounded-xl text-center space-y-3">
        <AlertTriangle className="w-10 h-10 mx-auto text-rose-500" />
        <h2 className="text-lg font-bold text-slate-900">Failed to load match score breakdown</h2>
        <p className="text-sm text-slate-600">{error || 'Data is unavailable.'}</p>
        <button
          onClick={handleBack}
          className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition-colors"
        >
          Back
        </button>
      </div>
    );
  }

  const { breakdown, match_score, interpretation, suggestions, algorithm_version, resume_filename, calculated_at } = scoreData;

  return (
    <div className="max-w-6xl mx-auto space-y-6 p-6 text-slate-800">
      
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <button 
            onClick={handleBack}
            className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-blue-600 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Match Scores
          </button>
          <h1 className="text-xl font-bold text-slate-900">
            ATS Match Score Analysis
          </h1>
        </div>
      </div>

      {/* Main Banner: Overall Score */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col sm:flex-row items-center justify-center gap-4 text-center">
        <span className="text-xl font-semibold text-slate-700">Overall Score:</span>
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-extrabold text-slate-900">
            {match_score !== null ? `${Math.round(match_score)}%` : 'N/A'}
          </span>
          <span className="text-lg font-bold text-emerald-600">[{interpretation}]</span>
        </div>
      </section>

      {/* 2x2 Grid Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Card 1: Hard Skills */}
        <article className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <header className="border-b border-slate-100 pb-2">
            <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-600" /> Hard Skills Score: {formatComponentScore(breakdown.hard_skills)}
            </h2>
          </header>
          {!breakdown.hard_skills.available ? (
            <p className="text-sm text-slate-500 italic">{breakdown.hard_skills.reason}</p>
          ) : (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-semibold text-slate-700 mb-2">Matched ({breakdown.hard_skills.matched_skills.length}):</p>
                <ul className="space-y-1 text-slate-600 list-disc list-inside">
                  {breakdown.hard_skills.matched_skills.map((skill, idx) => (
                    <li key={idx}>{skill}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-semibold text-slate-700 mb-2">Missing ({breakdown.hard_skills.missing_skills.length}):</p>
                <ul className="space-y-1 text-slate-600 list-disc list-inside">
                  {breakdown.hard_skills.missing_skills.map((skill, idx) => (
                    <li key={idx} className="text-slate-700">{skill}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </article>

        {/* Card 2: Soft Skills */}
        <article className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <header className="border-b border-slate-100 pb-2">
            <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <Users className="w-4 h-4 text-emerald-600" /> Soft Skills Score: {formatComponentScore(breakdown.soft_skills)}
            </h2>
          </header>
          {!breakdown.soft_skills.available ? (
            <p className="text-sm text-slate-500 italic">{breakdown.soft_skills.reason}</p>
          ) : (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-semibold text-slate-700 mb-2">Matched ({breakdown.soft_skills.matched_skills.length}):</p>
                <ul className="space-y-1 text-slate-600 list-disc list-inside">
                  {breakdown.soft_skills.matched_skills.map((skill, idx) => (
                    <li key={idx}>{skill}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-semibold text-slate-700 mb-2">Missing ({breakdown.soft_skills.missing_skills.length}):</p>
                <ul className="space-y-1 text-slate-600 list-disc list-inside">
                  {breakdown.soft_skills.missing_skills.map((skill, idx) => (
                    <li key={idx}>{skill}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </article>

        {/* Card 3: Experience Score */}
        <article className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <header className="border-b border-slate-100 pb-2">
            <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-indigo-600" /> Experience Score: {formatComponentScore(breakdown.experience)}
            </h2>
          </header>
          {!breakdown.experience.available ? (
            <p className="text-sm text-slate-500 italic">{breakdown.experience.reason}</p>
          ) : (
            <div className="text-sm space-y-1 text-slate-600">
              <p><span className="font-medium text-slate-700">Your Experience:</span> {breakdown.experience.user_experience}</p>
              <p><span className="font-medium text-slate-700">Required:</span> {breakdown.experience.required_experience}</p>
            </div>
          )}
        </article>

        {/* Card 4: Keyword Density */}
        <article className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <header className="border-b border-slate-100 pb-2">
            <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-amber-600" /> Keyword Density: {formatComponentScore(breakdown.keyword_density)}
            </h2>
          </header>
          <div className="text-sm text-slate-600">
            {breakdown.keyword_density.available ? (
              <p>Share of the job posting's vocabulary this resume actually uses.</p>
            ) : (
              <p className="italic text-slate-500">{breakdown.keyword_density.reason}</p>
            )}
          </div>
        </article>

      </div>

      {/* Suggestions Section */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-600" /> Suggestions for Improvement:
        </h2>
        <ul className="space-y-2 text-sm list-disc list-inside text-slate-700">
          {suggestions.map((item, idx) => (
            <li key={idx} className="leading-relaxed">{item}</li>
          ))}
        </ul>
      </section>

      {/* Footer Controls */}
      <footer className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-200 pt-4 text-xs text-slate-500">
        <div>
          <span>Algorithm: <strong>{algorithm_version}</strong></span>
          <span className="mx-2">|</span>
          <span>Resume: <strong>{resume_filename || 'Active Resume'}</strong></span>
          <span className="mx-2">|</span>
          <span>Calculated: <strong>{new Date(calculated_at).toLocaleDateString()}</strong></span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RotateCw className={`w-3.5 h-3.5 ${recalculating ? 'animate-spin' : ''}`} />
            Recalculate Score
          </button>
          
          <button 
            onClick={() => window.print()}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Export as PDF
          </button>

          <button 
            onClick={handleBack}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-lg transition-colors"
          >
            Back
          </button>
        </div>
      </footer>

    </div>
  );
};

export default MatchScoreDetail;