// src/context/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect } from "react";
import { apiClient } from "../api/client";

interface User {
  id: number;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // 1. Verify session on app startup / page refresh
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Calls your /users/me endpoint which relies on the HttpOnly cookie
        const response = await apiClient.get<User>("/users/me");
        setUser(response.data);
      } catch {
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  // 2. Login method using Form Data (required by OAuth2PasswordRequestForm)
  const login = async (email: string, password: string) => {
    // OAuth2PasswordRequestForm expects URLSearchParams / form-urlencoded data
    const formData = new URLSearchParams();
    formData.append("username", email); // Note: 'username' field holds the email
    formData.append("password", password);

    // Send login request as form data
    await apiClient.post("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    // After login success & cookie setting, fetch user profile
    const userResponse = await apiClient.get<User>("/users/me");
    setUser(userResponse.data);
  };

  // 3. Logout method
  const logout = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};