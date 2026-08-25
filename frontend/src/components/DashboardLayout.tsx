// src/components/DashboardLayout.tsx
import React from "react";
import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

export const DashboardLayout: React.FC = () => {
  return (
    // 1. Lock screen height to 100vh and prevent outer window scrolling
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-50">
      
      {/* 2. Top Header / Navbar (Fixed height, stays anchored at top) */}
      <header className="flex-shrink-0 z-10">
        <Navbar />
      </header>

      {/* 3. Body Container: Takes up all remaining vertical space */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        
        {/* 4. Left Sidebar (Stays fixed on left under the Navbar) */}
        <aside className="w-64 flex-shrink-0 bg-white border-r border-slate-200 overflow-y-auto">
          <Sidebar />
        </aside>

        {/* 5. Main Content Area (THIS IS THE ONLY PART THAT SCROLLS) */}
        <main className="flex-1 p-6 lg:p-10 overflow-y-auto">
          <Outlet />
        </main>

      </div>
    </div>
  );
};