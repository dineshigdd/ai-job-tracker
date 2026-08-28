import React, { useState, useRef, useEffect } from "react";
import { 
  Upload, 
  Trash2, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Loader2, 
  FileText, 
  Star 
} from "lucide-react";

import * as resumeApi from "../api/resume";
import { 
  ResumeSummary, 
  ResumeAnalysisResponse 
} from "../types/resume";

// interface StoredResume {
//   id: string;
//   filename: string;
//   is_active: boolean;
//   content_hash: string;
//   extracted_text_length: number;
// }

// interface KeyFinding {
//   text: string;
//   matched: boolean;
// }

// interface AnalysisResult {
//   filename?: string;
//   ai_feedback?: string;
//   match_score?: number;
//   assessment?: string;
//   key_findings?: KeyFinding[];
//   suggestions?: string[];
// }

export const ResumeAnalyzer: React.FC = () => {
  // State: Inputs
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [storedResumes, setStoredResumes] = useState<ResumeSummary[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>("");
  const [jobDescription, setJobDescription] = useState<string>("");
  const [selectedTrackedJob, setSelectedTrackedJob] = useState<string>("");

  // State: Operations & Results
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<ResumeAnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load user's resumes on mount
  useEffect(() => {
    fetchResumes();
  }, []);

  // GET /api/resumes/
  const fetchResumes = async () => {
    try {
      const response = await resumeApi.getResumeList();
      setStoredResumes(response);
      if (response.length > 0) {
        const active = response.find((r) => r.is_active) || response[0];
        setSelectedResumeId(active.id);
      }
    } catch (err) {
      console.error("Failed to fetch resumes:", err);
    }
  };

  // DELETE /api/resumes/{resume_id}
  const handleDeleteResume = async (resumeId: string) => {
    if (!window.confirm("Are you sure you want to delete this resume?")) return;
    try {
      await resumeApi.deleteResume(resumeId);
      await fetchResumes();
    } catch (err) {
      setErrorMessage("Failed to delete resume.");
    }
  };

  // PUT /api/resumes/{resume_id}/activate
  const handleActivateResume = async (resumeId: string) => {
    try {
      await resumeApi.makeResumeActive(resumeId);
      await fetchResumes();
    } catch (err) {
      setErrorMessage("Failed to set active resume.");
    }
  };

  // Drag and Drop Handlers
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf") {
        setSelectedFile(file);
        setErrorMessage("");
      } else {
        setErrorMessage("Please upload a valid PDF file.");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMessage("");
    }
  };

  // Main Submit Handler (Calls POST /resumes/analyze or POST /resumes/{resume_id}/analyze)
  const handleAnalyze = async () => {
    setErrorMessage("");
    setIsLoading(true);

    try {
      let response;

      // Option A: Upload & Analyze new PDF (POST /resumes/analyze)
      if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        if (jobDescription) {
          formData.append("job_description", jobDescription);
        }

        response = await resumeApi.uploadAndAnalyzeResume(selectedFile, jobDescription);

        await fetchResumes(); // Refresh database list
      } 
      // Option B: Analyze existing stored resume (POST /resumes/{resume_id}/analyze)
      else if (selectedResumeId) {
        response = await resumeApi.analyzeResumeById(selectedResumeId, jobDescription);
      } else {
        setErrorMessage("Please select a stored resume or upload a new PDF.");
        setIsLoading(false);
        return;
      }

      const data = response;
      // 2. Spread `data` so required fields like `resume` and `extracted_text_length` are included
      setAnalysisResult({
        ...data,
        filename: data.filename || data.resume?.filename || "Resume.pdf",
        ai_feedback: data.ai_feedback || "",
        match_score: data.match_score ?? 85,
        assessment: (data.match_score ?? 85) >= 80 ? "Excellent Match" : "Good Match",
        key_findings: data.key_findings || [
          { text: "Strong Python & FastAPI match", matched: true },
          { text: "Missing: Docker, Kubernetes", matched: false },
          { text: "8 years experience matches req.", matched: true },
        ],
        suggestions: data.suggestions || [
          "1. Add Docker experience",
          "2. Highlight cloud projects",
          "3. Quantify achievements",
        ],
      });
    } catch (err: any) {
      setErrorMessage(
        err?.response?.data?.detail || "An error occurred while analyzing the resume."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="space-y-8">
      {/* Page Header */}
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800">
          AI Resume Analyzer & Match Scorer
        </h1>
      </header>

      {/* Error Banner */}
      {errorMessage && (
        <aside 
          aria-label="Error message" 
          className="mb-4 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg flex items-center gap-2"
        >
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p className="text-sm">{errorMessage}</p>
        </aside>
      )}

      {/* Main Grid Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ================= LEFT COLUMN: RESUME INPUT ================= */}
        <section aria-labelledby="resume-input-heading" className="space-y-6">
          <header>
            <h2 id="resume-input-heading" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              LEFT COLUMN: Resume Input
            </h2>
          </header>

          {/* Card 1: Upload New Resume */}
          <article className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-800">Upload New Resume</h3>
            
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-blue-400 rounded-lg p-6 text-center transition cursor-pointer bg-slate-50 flex flex-col items-center justify-center gap-2"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileSelect}
              />
              <Upload className="w-6 h-6 text-slate-400" />
              <p className="text-sm text-slate-500 font-medium">
                {selectedFile ? (
                  <span className="text-blue-600 font-semibold">{selectedFile.name}</span>
                ) : (
                  "[ Drag & Drop PDF Here ]"
                )}
              </p>
              <button
                type="button"
                className="mt-1 px-4 py-1.5 text-xs font-semibold text-slate-700 border border-slate-300 rounded bg-white hover:bg-slate-50 shadow-sm"
              >
                Browse Files
              </button>
            </div>
          </article>

          {/* Card 2: Stored Resumes */}
          <article className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-800">
              Stored Resumes (Max 25)
            </h3>

            {/* Resume Items List */}
            <ul className="space-y-2">
              {storedResumes.map((res) => (
                <li
                  key={res.id}
                  className="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-md text-sm text-slate-700"
                >
                  <span className="truncate flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                    {res.is_active && (
                      <strong className="text-blue-600 font-bold">[Active] </strong>
                    )}
                    <span className="truncate">{res.filename}</span>
                  </span>

                  <nav aria-label="Resume actions" className="flex items-center gap-2 shrink-0">
                    {!res.is_active && (
                      <button 
                        type="button"
                        onClick={() => handleActivateResume(res.id)}
                        className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
                        title="Set as Active Resume"
                      >
                        <Star className="w-3.5 h-3.5" />
                        Set Active
                      </button>
                    )}
                    <button 
                      type="button"
                      onClick={() => handleDeleteResume(res.id)}
                      className="text-slate-400 hover:text-red-600 transition p-1"
                      title="Delete Resume"
                      aria-label={`Delete ${res.filename}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </nav>
                </li>
              ))}
            </ul>

            {/* Selection Dropdown */}
            <div className="flex items-center gap-2 pt-2">
              <label htmlFor="stored-resume-select" className="text-sm font-medium text-slate-700 shrink-0">
                Select:
              </label>
              <select
                id="stored-resume-select"
                value={selectedResumeId}
                onChange={(e) => {
                  setSelectedResumeId(e.target.value);
                  setSelectedFile(null); // Clear manual file upload selection when switching
                }}
                className="w-full text-sm border border-slate-300 rounded-md p-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {storedResumes.map((res) => (
                  <option key={res.id} value={res.id}>
                    {res.filename}
                  </option>
                ))}
              </select>
            </div>
          </article>

          {/* Card 3: Target Job Description & Analyze Action */}
          <article className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <label htmlFor="job-description-input" className="block text-sm font-bold text-slate-800 mb-2">
                Target Job Description:
              </label>
              <textarea
                id="job-description-input"
                rows={4}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="[ Paste job description... ]"
                className="w-full text-sm border border-slate-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-700"
              />
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="tracked-job-select" className="text-sm text-slate-600 whitespace-nowrap">
                OR Select from tracked jobs:
              </label>
              <select
                id="tracked-job-select"
                value={selectedTrackedJob}
                onChange={(e) => setSelectedTrackedJob(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-md p-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Google - Backend Eng</option>
                <option value="meta">Meta - Frontend Eng</option>
                <option value="amazon">Amazon - Fullstack Eng</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleAnalyze}
              disabled={isLoading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition shadow flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Analyzing Resume...</span>
                </>
              ) : (
                "Analyze Resume"
              )}
            </button>
          </article>
        </section>

        {/* ================= RIGHT COLUMN: AI RESULTS ================= */}
        <section aria-labelledby="ai-results-heading" className="space-y-6">
          <header>
            <h2 id="ai-results-heading" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              RIGHT COLUMN: AI Results
            </h2>
          </header>

          {/* Match Score & Assessment Display */}
          <article className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-center flex flex-col items-center">
            {/* SVG Progress Circle */}
            <figure className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-slate-100"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-emerald-500 stroke-current transition-all duration-500"
                  strokeWidth="3.5"
                  strokeDasharray={`${analysisResult?.match_score ?? 85}, 100`}
                  strokeLinecap="round"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <figcaption className="absolute flex flex-col items-center justify-center">
                <span className="text-xs text-slate-400 font-medium">( O )</span>
                <span className="text-2xl font-extrabold text-slate-800">
                  {analysisResult?.match_score ?? 85}%
                </span>
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Match</span>
              </figcaption>
            </figure>

            <div className="mt-4">
              <p className="text-sm text-slate-600 font-medium">Overall Assessment:</p>
              <p className="text-lg font-bold text-emerald-600">
                [{analysisResult?.assessment ?? "Excellent Match"}]
              </p>
            </div>
          </article>

          {/* Key Findings Card */}
          <article className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-800">Key Findings:</h3>
            <ul className="space-y-2 text-sm text-slate-700">
              {analysisResult?.key_findings ? (
                analysisResult.key_findings.map((item, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    {item.matched ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                    )}
                    <span>{item.text}</span>
                  </li>
                ))
              ) : (
                <>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>Strong Python &amp; FastAPI match</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                    <span>Missing: Docker, Kubernetes</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>8 years experience matches req.</span>
                  </li>
                </>
              )}
            </ul>
          </article>

          {/* AI Suggestions Card */}
          <article className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-800">AI Suggestions:</h3>
            <ol className="space-y-1.5 text-sm text-slate-700 pl-1">
              {analysisResult?.suggestions ? (
                analysisResult.suggestions.map((sug, idx) => (
                  <li key={idx}>{sug}</li>
                ))
              ) : (
                <>
                  <li>1. Add Docker experience</li>
                  <li>2. Highlight cloud projects</li>
                  <li>3. Quantify achievements</li>
                </>
              )}
            </ol>
          </article>

          {/* Action Button */}
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={isLoading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition shadow flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Calculating...</span>
              </>
            ) : (
              "Calculate Match Score"
            )}
          </button>
        </section>

      </div>
    </main>
  );
};

export default ResumeAnalyzer;