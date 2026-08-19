import React from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const stats = {
    totalApplications: 24,
    interviewsScheduled: 5,
    offersReceived: 2,
    responseRate: "37.5%",
  };

  const recentApplications = [
    { id: 1, company: "TechCorp Inc.", role: "Senior Backend Developer", status: "Interviewing", date: "2026-06-12" },
    { id: 2, company: "CloudScale AI", role: "Full Stack Engineer", status: "Applied", date: "2026-06-15" },
    { id: 3, company: "DataFlow Systems", role: "Python Developer", status: "Offer", date: "2026-06-08" },
    { id: 4, company: "InnoVate Labs", role: "Backend Architect", status: "Rejected", date: "2026-06-01" },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Interviewing": return "bg-amber-100 text-amber-800";
      case "Offer": return "bg-emerald-100 text-emerald-800";
      case "Applied": return "bg-blue-100 text-blue-800";
      case "Rejected": return "bg-rose-100 text-rose-800";
      default: return "bg-slate-100 text-slate-800";
    }
  };

  return (
    // 1. Root Container: Stacks Navbar on top and Body below
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-50">
      
      {/* Top Navbar - Takes full 100% width */}
      <Navbar title="Dashboard" userEmail="developer@example.com" />

      {/* 2. Bottom Container: Horizontal flex for Sidebar + Main Content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        
        {/* Left Sidebar (Below Navbar) */}
        <Sidebar />

        {/* Right Scrollable Workspace */}
        <main className="flex-1 p-6 lg:p-10 overflow-y-auto">
          {/* Section Header */}
          <header className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900">Application Dashboard</h2>
            <p className="text-sm text-slate-500">Track your job hunt pipeline and AI-matched metrics.</p>
          </header>

          {/* Overview Stats Grid */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Total Applications</p>
              <p className="text-3xl font-extrabold text-slate-900 mt-2">{stats.totalApplications}</p>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Interviews Scheduled</p>
              <p className="text-3xl font-extrabold text-amber-600 mt-2">{stats.interviewsScheduled}</p>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Offers Received</p>
              <p className="text-3xl font-extrabold text-emerald-600 mt-2">{stats.offersReceived}</p>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-sm font-medium text-slate-500">Response Rate</p>
              <p className="text-3xl font-extrabold text-blue-600 mt-2">{stats.responseRate}</p>
            </div>
          </section>

          {/* Quick Actions Section */}
          <section className="mb-8">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Quick Actions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => navigate("/jobs")}
                className="p-5 bg-white border border-slate-200 rounded-xl text-left hover:border-blue-500 hover:shadow-md transition-all group"
              >
                <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center font-bold text-lg mb-3 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  +
                </div>
                <h4 className="font-semibold text-slate-900">Add Job Application</h4>
                <p className="text-xs text-slate-500 mt-1">Record a new role in your tracking pipeline.</p>
              </button>

              <button
                onClick={() => navigate("/resumes/analyze")}
                className="p-5 bg-white border border-slate-200 rounded-xl text-left hover:border-blue-500 hover:shadow-md transition-all group"
              >
                <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-lg flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                  AI
                </div>
                <h4 className="font-semibold text-slate-900">Analyze Resume</h4>
                <p className="text-xs text-slate-500 mt-1">Optimize your resume using AI recommendations.</p>
              </button>

              <button
                onClick={() => navigate("/match-score")}
                className="p-5 bg-white border border-slate-200 rounded-xl text-left hover:border-blue-500 hover:shadow-md transition-all group"
              >
                <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                  %
                </div>
                <h4 className="font-semibold text-slate-900">Check Match Score</h4>
                <p className="text-xs text-slate-500 mt-1">Compare your profile against job descriptions.</p>
              </button>
            </div>
          </section>          
          {/* Recent Applications Table with Single Pagination */}
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {/* Table Header */}
            <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-bold text-slate-900">Recent Applications</h3>
              <button 
                onClick={() => navigate("/jobs")}
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
              >
                View All →
              </button>
            </div>

            {/* Table Body */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                    <th className="py-3 px-6">Company</th>
                    <th className="py-3 px-6">Role</th>
                    <th className="py-3 px-6">Status</th>
                    <th className="py-3 px-6">Date Applied</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
                  {recentApplications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 font-medium text-slate-900">{app.company}</td>
                      <td className="py-4 px-6">{app.role}</td>
                      <td className="py-4 px-6">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusBadge(app.status)}`}>
                          {app.status}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-slate-500">{app.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Single Clean Pagination Footer */}
            <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Showing 1 to 4 of 24 applications</span>
              <div className="flex space-x-2">
                <button className="px-3 py-1.5 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">
                  Previous
                </button>
                <button className="px-3 py-1.5 border border-slate-200 rounded-lg hover:bg-slate-50">
                  Next
                </button>
              </div>
            </div>
          </section>
          
        </main>
      </div>
    </div>
  );
};

export default Dashboard;