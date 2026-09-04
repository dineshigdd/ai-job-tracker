import React, { useState, useEffect } from "react";
import { getJobApplications } from "../api/jobs";
import { type JobResponse } from "../types/job";
import { useNavigate, Link } from "react-router-dom";
// import { Plus, Briefcase, ChevronRight } from "lucide-react"; // Optional: Lucide icons for extra polish

const JobList: React.FC = () => {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setIsLoading(true);
        const data = await getJobApplications();
        setJobs(data);
      } catch (err: any) {
        setError("Failed to load applications. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, []);

  if (isLoading) {
    return (
      <div className="p-12 text-center text-slate-500 font-medium">
        Loading applications...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-12 text-center text-rose-500 font-medium">
        {error}
      </div>
    );
  }

  return (
    <main className="space-y-6">
      {/* Top Header Row with Action Button Aligned Right */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Job Applications</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track and manage your target positions.
          </p>
        </div>

        {/* Primary "+ Add Job" Button -> direct to /jobs/new */}
        <Link
          to="/jobs/new"
          className="inline-flex items-center justify-center space-x-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors shrink-0"
        >
          <span className="text-base font-bold leading-none">+</span>
          <span>Add Job</span>
        </Link>
      </header>

      {/* Conditional Rendering for Empty State vs Table */}
      {jobs?.length === 0 ? (
        /* Enhanced Empty State UX */
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm space-y-4">
          <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto">
            <span className="text-xl font-bold">💼</span>
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-slate-900">
              No job applications yet
            </h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto">
              Get started by adding your first application to track your status, interviews, and resume match scores.
            </p>
          </div>
          <Link
            to="/jobs/new"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors"
          >
            <span>+ Add Your First Job</span>
          </Link>
        </div>
      ) : (
        /* Applications Table */
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3.5 font-semibold">Company</th>
                <th className="px-6 py-3.5 font-semibold">Role</th>
                <th className="px-6 py-3.5 font-semibold">Status</th>
                <th className="px-6 py-3.5 font-semibold">Applied/Created</th>
                <th className="px-6 py-3.5 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="cursor-pointer hover:bg-slate-50/80 transition-colors group"
                >
                  <td className="px-6 py-4 font-semibold text-slate-900">
                    {job.company_name}
                  </td>
                  <td className="px-6 py-4 text-slate-700 font-medium">
                    {job.job_title}
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
                      {job.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500">
                    {new Date(job.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right text-slate-400 group-hover:text-blue-600 font-medium text-xs">
                    View →
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
};

export default JobList;