// src/components/ProtectedRoute.tsx
import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // 1. While waiting for /api/users/me response on refresh, show a loader
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 font-medium">
        Loading...
      </div>
    );
  }

  // 2. If user is logged in, allow access to nested routes (<Outlet />);
  //    otherwise redirect them to /login
  return isAuthenticated ? <Outlet /> : <Navigate to="/users/login" replace />;
};