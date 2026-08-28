import React, { useState, useEffect } from "react";
import { getJobApplications } from "../api/jobs";
import { type JobResponse } from "../types/job";
import { useNavigate } from "react-router-dom";
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
    return <div className="p-10 text-center text-slate-500">Loading applications...</div>;
  }

  if (error) {
    return <div className="p-10 text-center text-rose-500">{error}</div>;
  }

  return (
    <main className="space-y-8">
       <header>
        <h2 className="text-2xl font-bold text-slate-900">Job Applications</h2>
        <p className="text-sm text-slate-500">List of your job applications.</p>
      </header>
      {jobs.length === 0 ? (
        <p className="text-slate-500">No job applications found.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">Company</th>
                <th className="px-6 py-3 font-medium">Role</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((job) => (
                <tr key={job.id}
                    onClick={() => navigate(`/jobs/${job.id}`)}
                    className="cursor-pointer hover:bg-slate-50 transition-colors duration-200">
                  <td className="px-6 py-4 font-medium text-slate-900">{job.company_name}</td>
                  <td className="px-6 py-4 text-slate-700">{job.job_title}</td>
                  <td className="px-6 py-4 text-slate-700">{job.status}</td>
                  <td className="px-6 py-4 text-slate-500">
                    {new Date(job.created_at).toLocaleDateString()}
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