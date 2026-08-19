import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;

  const navItems = [
    { label: "Dashboard", path: "/dashboard/stats" },
    { label: "Jobs List", path: "/jobs" },
    { label: "Resume AI", path: "/resumes/analyze" },
    { label: "Profile", path: "/users/me" },
    { label: "Match Score", path: "/match-score" },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 hidden md:flex flex-col justify-between shrink-0 min-h-screen">
      <div className="p-6">       

        {/* Navigation Links */}
        <nav className="space-y-1.5">
          {navItems.map((item) => (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-colors ${
                currentPath === item.path
                  ? "bg-blue-50 text-blue-600 font-semibold"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Sign Out Footer */}
      <div className="p-6 border-t border-slate-100">
        <Link
          to="/users/login"
          className="w-full flex justify-center items-center py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
        >
          Sign Out
        </Link>
      </div>
    </aside>
  );
};

export default Sidebar;