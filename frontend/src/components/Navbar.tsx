import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

interface NavbarProps {
  title?: string;
  userEmail?: string;
}

const Navbar: React.FC<NavbarProps> = ({
  title = "",
  userEmail = "user@example.com",
}) => {
  const navigate = useNavigate();
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
      {/* Left: Brand Header & Page Title */}
      <div className="flex items-center space-x-6">
        {/* Brand Header */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-sm">
            AI
          </div>
          <span className="text-xl font-bold text-slate-900 tracking-tight">
            JobTracker
          </span>
        </div>

        {/* Vertical Divider */}
        <div className="h-5 w-px bg-slate-200" />

        {/* Page Title */}
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          {title}
        </h1>
      </div>

      {/* Right: Actions & User Avatar */}
      <div className="flex items-center space-x-4">
        {/* "+ Add Job" Primary Button */}
        <button
          onClick={() => navigate("/jobs")}
          className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors"
        >
          <span className="text-base font-bold">+</span>
          <span>Add Job</span>
        </button>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center space-x-3 focus:outline-none p-1 rounded-lg hover:bg-slate-50 transition-colors"
          >
            {/* Circle Avatar with Initials */}
            <div className="w-9 h-9 bg-slate-900 text-white rounded-full flex items-center justify-center font-semibold text-xs border border-slate-200">
              {userEmail.substring(0, 2).toUpperCase()}
            </div>
            {/* Dropdown Arrow Indicator */}
            <svg
              className={`w-4 h-4 text-slate-500 transition-transform ${
                isProfileOpen ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {/* User Profile Dropdown Menu */}
          {isProfileOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-100 py-1 z-20">
              <div className="px-4 py-3 border-b border-slate-100">
                <p className="text-xs text-slate-400 font-medium">Signed in as</p>
                <p className="text-sm font-semibold text-slate-800 truncate">
                  {userEmail}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsProfileOpen(false);
                  navigate("/users/me");
                }}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Profile Settings
              </button>
              <button
                onClick={() => {
                  setIsProfileOpen(false);
                  navigate("/users/login");
                }}
                className="w-full text-left px-4 py-2 text-sm text-rose-600 hover:bg-rose-50 transition-colors border-t border-slate-100"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;