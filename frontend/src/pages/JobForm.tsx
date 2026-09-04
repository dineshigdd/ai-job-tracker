import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import * as JobAPI from "../api/jobs";
import { type JobCreate, type JobUpdate, type JobStatus, STATUS_ORDER } from "../types/job";

interface FormState {
  company_name: string;
  job_title: string;
  job_description: string;
  status: JobStatus;
  interview_date: string;
}

const JobForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditMode = Boolean(id);

  const [formData, setFormData] = useState<FormState>({
    company_name: "",
    job_title: "",
    job_description: "",
    status: "Applied",
    interview_date: "",
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // If in edit mode, fetch existing job details to populate the form
  useEffect(() => {
    if (!id) return;

    const fetchJob = async () => {
      setIsLoading(true);
      try {
        const job = await JobAPI.getJobApplicationById(id);
        setFormData({
          company_name: job.company_name || "",
          job_title: job.job_title || "",
          job_description: job.job_description || "",
          status: job.status || "Applied",
          interview_date: job.interview_date
            ? new Date(job.interview_date).toISOString().slice(0, 16)
            : "",
        });
      } catch (error) {
        console.error("Failed to fetch job details:", error);
        alert("Failed to load existing job details.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchJob();
  }, [id]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.SubmitEvent<HTMLFormElement>, targetStatus?: JobStatus) => {
    e.preventDefault();

    if (!formData.company_name.trim() || !formData.job_title.trim()) {
      alert("Please fill in both Company Name and Job Title.");
      return;
    }

    setIsSubmitting(true);

    // Format fields according to API schemas
    const finalStatus = targetStatus || formData.status;
    const formattedInterviewDate = formData.interview_date
      ? new Date(formData.interview_date).toISOString()
      : null;

    try {
      if (isEditMode && id) {
        // Edit Mode: Update Job
        const updatePayload: JobUpdate = {
          company_name: formData.company_name,
          job_title: formData.job_title,
          job_description: formData.job_description || null,
          status: finalStatus,
          interview_date: formattedInterviewDate,
        };
        await JobAPI.updateJobApplication(id, updatePayload);
      } else {
        // Create Mode: New Job
        const createPayload: JobCreate = {
          company_name: formData.company_name,
          job_title: formData.job_title,
          job_description: formData.job_description || null,
          status: finalStatus,
          interview_date: formattedInterviewDate,
        };
        await JobAPI.createJobApplication(createPayload);
      }

      navigate("/jobs");
    } catch (error) {
      console.error("Failed to save job application:", error);
      alert("An error occurred while saving the job application.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500 font-medium">
        Loading form...
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Bar with Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/jobs"
          className="inline-flex items-center text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors"
        >
          [ ← Back to Jobs ]
        </Link>
      </div>

      <form onSubmit={(e) => handleSubmit(e)} className="space-y-6">
        {/* Company Information Card */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-lg font-bold text-slate-800 border-b border-slate-100 pb-2">
            Company Information
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Company Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Company Name<span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                name="company_name"
                value={formData.company_name}
                onChange={handleChange}
                placeholder="Google"
                required
                className="w-full px-3 py-2 text-sm bg-emerald-50/40 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
            </div>

            {/* Job Title */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Job Title<span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                name="job_title"
                value={formData.job_title}
                onChange={handleChange}
                placeholder="Senior Backend Engineer"
                required
                className="w-full px-3 py-2 text-sm bg-emerald-50/40 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
            </div>
          </div>

          {/* Job Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Job Description (Optional - for AI features)
            </label>
            <textarea
              name="job_description"
              value={formData.job_description}
              onChange={handleChange}
              rows={3}
              placeholder="We're looking for a Senior Backend Engineer with..."
              className="w-full px-3 py-2 text-sm bg-emerald-50/40 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 resize-y"
            />
          </div>
        </div>

        {/* Application Details Card */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-lg font-bold text-slate-800 border-b border-slate-100 pb-2">
            Application Details
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Status Dropdown */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Status<span className="text-rose-500">*</span>
              </label>
              <select
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 font-medium"
              >
                {STATUS_ORDER.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>

            {/* Interview Date */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Interview Date (Optional)
              </label>
              <input
                type="datetime-local"
                name="interview_date"
                value={formData.interview_date}
                onChange={handleChange}
                className="w-full px-3 py-2 text-sm bg-emerald-50/40 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
            </div>
          </div>
        </div>

        {/* Action Footer */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={() => navigate("/jobs")}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 transition"
          >
            [ Cancel ]
          </button>
          
          <button
            type="button"
            onClick={(e) => handleSubmit(e, "Wishlist")}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-semibold text-slate-700 hover:text-blue-600 transition disabled:opacity-50"
          >
            [ Save as Draft ]
          </button>

          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition disabled:opacity-50"
          >
            {isSubmitting
              ? "Saving..."
              : isEditMode
              ? "[ Save Changes ]"
              : "[ Submit Application ]"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default JobForm;