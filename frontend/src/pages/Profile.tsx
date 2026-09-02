// src/pages/Profile.tsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as UserAPI from "../api/user";
import { Camera, AlertTriangle } from "lucide-react";

export const Profile: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Form States (Replaced fullName with firstName and lastName)
  const [firstName, setFirstName] = useState<string>("");
  const [lastName, setLastName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [currentPassword, setCurrentPassword] = useState<string>("");
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");

  // Operation States
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Sync user context data into form state
  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || "Sarah");
      setLastName(user.last_name || "Jenkins");
      setEmail(user.email || "sarah@example.com");
    }
  }, [user]);

  // PUT /users/me
  const handleSaveChanges = async (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    setMessage(null);

    if (newPassword && newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "New passwords do not match." });
      return;
    }

    try {
      setIsSaving(true);
      await UserAPI.updateUserProfile({
        first_name: firstName,
        last_name: lastName,
        email: email,
        ...(newPassword ? { password: newPassword } : {}),
      });

      setMessage({ type: "success", text: "Profile updated successfully!" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Failed to update profile. Please try again.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  // DELETE /users/me
  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to delete your account? All jobs, resumes, and data will be permanently wiped."
    );

    if (!confirmed) return;

    try {
      setIsDeleting(true);
      await UserAPI.deleteUserAccount();
      await logout();
      navigate("/login");
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Failed to delete account. Please try again.",
      });
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">Account Settings & Profile</h1>
      </header>

      {/* Global Status Message Alert */}
      {message && (
        <div
          className={`p-4 rounded-xl text-sm font-medium ${
            message.type === "success"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-rose-50 text-rose-700 border border-rose-200"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 1. Profile Information Section (PUT /users/me) */}
      <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 flex justify-between items-center">
          <h2 className="font-semibold text-slate-800 text-sm">
            Profile Information <span className="text-xs font-mono text-slate-500">(PUT /users/me)</span>
          </h2>
          <span className="text-xs text-slate-500 font-medium">User since: January 2026</span>
        </div>

        <form onSubmit={handleSaveChanges} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left: Avatar Column */}
            <div className="flex flex-col items-center justify-center space-y-3">
              <span className="text-xs font-semibold text-slate-500 self-start">Avatar</span>
              <div className="w-28 h-28 rounded-full bg-slate-200 flex items-center justify-center text-slate-400 border-2 border-slate-100">
                <svg className="w-16 h-16 fill-current" viewBox="0 0 24 24">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                </svg>
              </div>
              <button
                type="button"
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium transition shadow-sm"
              >
                <Camera className="w-3.5 h-3.5" />
                <span>Upload Photo</span>
              </button>
            </div>

            {/* Right: Input Fields Table / Grid */}
            <div className="md:col-span-2 space-y-3 text-sm">
              {/* First Name */}
              <div className="grid grid-cols-3 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <label className="font-medium text-slate-700">First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="col-span-2 px-3 py-1 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Last Name */}
              <div className="grid grid-cols-3 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <label className="font-medium text-slate-700">Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="col-span-2 px-3 py-1 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Email */}
              <div className="grid grid-cols-3 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <label className="font-medium text-slate-700">Email</label>
                <div className="col-span-2 flex items-center space-x-2">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="flex-1 px-3 py-1 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-xs font-semibold text-emerald-600 shrink-0">[Verified]</span>
                </div>
              </div>

              {/* Current Password */}
              <div className="grid grid-cols-3 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <label className="font-medium text-slate-700">Current Password</label>
                <input
                  type="password"
                  placeholder="••••••••••••••••"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="col-span-2 px-3 py-1 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* New Password */}
              <div className="grid grid-cols-3 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <label className="font-medium text-slate-700">New Password</label>
                <input
                  type="password"
                  placeholder="••••••••••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="col-span-2 px-3 py-1 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Confirm New Password */}
              <div className="grid grid-cols-3 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <label className="font-medium text-slate-700">Confirm New Password</label>
                <input
                  type="password"
                  placeholder="••••••••••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="col-span-2 px-3 py-1 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Submit Action */}
          <div className="text-center pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm transition shadow-sm disabled:opacity-50"
            >
              {isSaving ? "[ Saving... ]" : "[ Save Changes ]"}
            </button>
          </div>
        </form>
      </section>

      {/* 2. Storage Usage Section */}
      <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3">
          <h2 className="font-semibold text-slate-800 text-sm">Storage Usage</h2>
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-3 text-center text-sm font-medium text-slate-700 gap-4">
          <div>Resumes Stored: <span className="font-semibold text-slate-900">3 / 25</span></div>
          <div>Job Applications: <span className="font-semibold text-slate-900">24</span></div>
          <div>Total Storage: <span className="font-semibold text-slate-900">12.5 MB / 50 MB</span></div>
        </div>
      </section>

      {/* 3. API Access Section */}
      <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3">
          <h2 className="font-semibold text-slate-800 text-sm">API Access</h2>
        </div>
        <div className="p-6 space-y-3">
          <div className="flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-3">
            <span className="font-medium text-slate-700 text-sm min-w-[80px]">API Key</span>
            <input
              type="password"
              readOnly
              value="••••••••••••••••••••"
              className="flex-1 px-3 py-1.5 border border-slate-200 bg-blue-50/50 rounded-lg text-sm text-slate-800"
            />
            <div className="flex space-x-2">
              <button
                type="button"
                className="px-3 py-1.5 bg-slate-600 hover:bg-slate-700 text-white rounded-lg text-xs font-medium transition"
              >
                [ Regenerate ]
              </button>
              <button
                type="button"
                className="px-3 py-1.5 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium transition"
              >
                [ Copy ]
              </button>
            </div>
          </div>
          <p className="text-xs text-slate-500">Rate Limit: 100 requests/hour</p>
        </div>
      </section>

      {/* 4. Danger Zone Section (DELETE /users/me) */}
      <section className="bg-rose-50/60 rounded-xl border border-rose-200 shadow-sm overflow-hidden">
        <div className="bg-rose-100/70 border-b border-rose-200 px-6 py-3 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-600" />
          <h2 className="font-bold text-rose-800 text-sm">
            Danger Zone <span className="font-mono text-xs font-normal text-rose-600">(DELETE /users/me)</span>
          </h2>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Delete Account</h3>
            <p className="text-xs text-slate-600 mt-1">
              Once you delete your account, all data including jobs, resumes, and match scores will be permanently wiped. This cannot be undone.
            </p>
          </div>
          <div className="text-center">
            <button
              onClick={handleDeleteAccount}
              disabled={isDeleting}
              className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-medium rounded-lg text-sm transition shadow-sm disabled:opacity-50"
            >
              {isDeleting ? "Deleting..." : "I understand, delete my account"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Profile;