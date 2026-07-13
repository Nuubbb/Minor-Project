import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { setAuthToken } from "../api/client";
import * as authApi from "../api/auth";
import { AuthUser, Role } from "../types";

const STORAGE_KEY = "surveillance_auth";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (role: Role, username: string, password: string) => Promise<void>;
  signup: (username: string, password: string, email: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        if (raw) {
          const stored: AuthUser = JSON.parse(raw);
          setAuthToken(stored.token);
          setUser(stored);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const persist = useCallback(async (nextUser: AuthUser | null) => {
    setAuthToken(nextUser?.token ?? null);
    setUser(nextUser);
    if (nextUser) {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser));
    } else {
      await AsyncStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const login = useCallback(
    async (role: Role, username: string, password: string) => {
      const authUser = await authApi.login(role, username, password);
      await persist(authUser);
    },
    [persist]
  );

  const signup = useCallback(async (username: string, password: string, email: string) => {
    await authApi.signup(username, password, email);
  }, []);

  const logout = useCallback(async () => {
    await persist(null);
  }, [persist]);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
