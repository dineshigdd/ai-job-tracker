import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";

// Import your page views
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import JobList from "./pages/JobList";
import ResumeAnalyzer from "./pages/ResumeAnalyzer";
import Profile from "./pages/Profile";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardLayout } from "./components/DashboardLayout";
// Define your clean routing map without duplicates or self-loops
const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/users/login" replace />,
  },
  {
    path: "/login",
    element: <Navigate to="/users/login" replace />,
  },
  {
    path: "/users/login",
    element: <Login />,
  },
  {
    path: "/users/register",
    element: <Register />,
  },

  //Protected Routes (Only accessible when logged in)
  {
    element: <ProtectedRoute />,
    children: [
      {
          element: <DashboardLayout />,
          children: [
          {
            path: "/dashboard/stats",
            element: <Dashboard />,
          },
          {
            path: "/jobs",
            element: <JobList />,
          },
          {
            path: "/resumes/analyze",
            element: <ResumeAnalyzer />,
          },
          {
            path: "/users/me",
            element: <Profile />,
          },
          ]
      }
      
    ],
  },

  // Fallback Catch-All Route
  {
    path: "*",
    element: <div className="p-8 text-center font-semibold">404 - Page Not Found</div>,
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;