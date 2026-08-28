// src/pages/JobDetail.tsx
import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import * as JobAPI from "../api/jobs";
import { type JobResponse, type JobStatus, STATUS_ORDER } from '../types/job';


const JobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<JobResponse | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<JobStatus>("Wishlist");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);
  const [isGeneratingCoverLetter, setIsGeneratingCoverLetter] = useState<boolean>(false);

  // Fetch job details on load
  useEffect(() => {
    const fetchJobDetail = async () => {
      if (!id) return;
      try {
        const data = await JobAPI.getJobApplicationById(id);
        setJob(data);
        setSelectedStatus(data.status);
      } catch (error) {
        console.error("Failed to load job details:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobDetail();
  }, [id]);

  // Handle status update using JobAPI.updateJobApplication
  const handleSaveStatus = async () => {
    if (!id || !job) return;
    setIsUpdatingStatus(true);
    try {
      const updatedJob = await JobAPI.updateJobApplication(id, {
        status: selectedStatus,
      });
      setJob(updatedJob);
      alert("Status updated successfully!");
    } catch (error) {
      console.error("Failed to update status:", error);
      alert("Failed to update status. Make sure the status value is valid.");
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  // Trigger Cover Letter Generation using JobAPI.generateCoverLetter
  const handleGenerateCoverLetter = async () => {
    if (!id) return;
    setIsGeneratingCoverLetter(true);
    try {
      const updatedJob = await JobAPI.generateCoverLetter(id);
      setJob(updatedJob);
    } catch (error) {
      console.error("Failed to generate cover letter:", error);
      alert("Failed to generate cover letter. Ensure a job description exists.");
    } finally {
      setIsGeneratingCoverLetter(false);
    }
  };

  // Delete Job using JobAPI.deleteJobApplication
  const handleDeleteJob = async () => {
    if (!id) return;
    if (window.confirm("Are you sure you want to delete this job application?")) {
      try {
        await JobAPI.deleteJobApplication(id);
        navigate("/jobs");
      } catch (error) {
        console.error("Failed to delete job:", error);
        alert("Failed to delete the job application.");
      }
    }
  };

  // Helper to render Status History
  const renderStatusHistory = () => {
    if (!job?.status_events || job.status_events.length === 0) {
      return <span>Wishlist &rarr; {job?.status}</span>;
    }

    return (
      <span>
        {job.status_events.map((event, idx) => (
          <React.Fragment key={event.id || idx}>
            {idx > 0 && " → "}
            <span className="font-semibold text-slate-800">{event.to_status}</span>
            <span className="text-slate-500">
              {" "}
              ({new Date(event.changed_at).toLocaleDateString()})
            </span>
          </React.Fragment>
        ))}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500 font-medium">
        Loading job details...
      </div>
    );
  }

  if (!job) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-slate-600 font-medium">Job not found.</p>
        <Link to="/jobs" className="text-blue-600 hover:underline inline-block">
          ← Back to Jobs
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back Button */}
      <div>
        <Link
          to="/jobs"
          className="inline-flex items-center text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors"
        >
          [ ← Back to Jobs ]
        </Link>
      </div>

      {/* Title Card */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">
          {job.company_name.toUpperCase()} - {job.job_title}
        </h1>
      </div>

      {/* Status Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
        <span className="font-semibold text-slate-700">Status:</span>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value as JobStatus)}
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-slate-50 text-emerald-700 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {STATUS_ORDER.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
        <button
          onClick={handleSaveStatus}
          disabled={isUpdatingStatus}
          className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
        >
          {isUpdatingStatus ? "Saving..." : "[ Save ]"}
        </button>
      </div>

      {/* Company & Job Details Overview */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <p>
          <span className="font-semibold text-slate-700">Company:</span>{" "}
          {job.company_name}
        </p>
        <p>
          <span className="font-semibold text-slate-700">Job Title:</span>{" "}
          {job.job_title}
        </p>
      </div>

      {/* Job Description */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <h3 className="font-semibold text-slate-900">Job Description:</h3>
        <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
          {job.job_description || "No job description provided."}
        </p>
      </div>

      {/* Application Details */}
      <div>
        <h3 className="text-lg font-bold text-slate-900 mb-3">
          Application Details:
        </h3>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2 text-sm text-slate-700">
          <p>
            <span className="font-semibold">Interview Date:</span>{" "}
            {job.interview_date
              ? new Date(job.interview_date).toLocaleDateString()
              : "Not scheduled"}
          </p>
          <p>
            <span className="font-semibold">Created At:</span>{" "}
            {job.created_at ? new Date(job.created_at).toLocaleDateString() : "N/A"}
          </p>
        </div>
      </div>

      {/* AI Features Section */}
      <div>
        <h3 className="text-lg font-bold text-slate-900 mb-3">AI Features:</h3>
        <div className="space-y-4">
          {/* Cover Letter Box */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800 flex items-center space-x-2">
                <span>📝</span> <span>Cover Letter</span>
              </span>
              <button
                onClick={handleGenerateCoverLetter}
                disabled={isGeneratingCoverLetter}
                className="text-sm font-semibold text-blue-600 hover:underline disabled:opacity-50"
              >
                {isGeneratingCoverLetter
                  ? "[ Generating... ]"
                  : job.ai_cover_letter
                  ? "[ Regenerate ]"
                  : "[ Generate Cover Letter ]"}
              </button>
            </div>

            {job.ai_cover_letter ? (
              <div className="mt-3 p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 whitespace-pre-line leading-relaxed">
                {job.ai_cover_letter}
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                No cover letter generated yet.
              </p>
            )}
          </div>

          {/* Match Score Box */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800 flex items-center space-x-2">
                <span>🎯</span> <span>Match Score</span>
              </span>
            </div>

            {job.match_score !== null && job.match_score !== undefined ? (
              <div className="pt-1">
                <span className="text-lg font-bold text-blue-600">
                  {job.match_score}% Match
                </span>
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                No match score calculated yet.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Status History Section */}
      <div>
        <h3 className="text-lg font-bold text-slate-900 mb-3">
          Status History:
        </h3>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-sm text-slate-700">
          {renderStatusHistory()}
        </div>
      </div>

      {/* Action Footer */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-center space-x-6 text-sm font-semibold text-blue-600">
        <button
          onClick={handleDeleteJob}
          className="text-rose-600 hover:underline"
        >
          [ Delete ]
        </button>
      </div>
    </div>
  );
};

export default JobDetail;