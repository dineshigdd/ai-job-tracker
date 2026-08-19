import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";

// Import your page views
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ResumeAnalyzer from "./pages/ResumeAnalyzer";
import Profile from "./pages/Profile";

// Define your clean routing map without duplicates or self-loops
const router = createBrowserRouter([
  {
    path: "/",
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
  {
    path: "/dashboard/stats",
    element: <Dashboard />,
  },
  {
    path: "/resumes/analyze",
    element: <ResumeAnalyzer />,
  },
  {
    path: "/users/me",
    element: <Profile />,
  },
  {
    path: "*",
    element: <div className="p-8 text-center font-semibold">404 - Page Not Found</div>,
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;