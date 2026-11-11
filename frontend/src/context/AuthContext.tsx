import React, { createContext, useContext, useEffect, useState } from 'react';
import { getStoredToken, isDemoPreviewToken, setStoredToken } from '../api/client';
import { demoSandbox } from '../api/demoSandbox';
import { authService } from '../api/services';
import type { LoginPayload, RegisterPayload, SupportedLanguage, User } from '../types/api';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isDemoSession: boolean;
  login: (payload: LoginPayload, demoRoleHint?: 'farmer' | 'admin') => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  enterDemoSandbox: (role: 'farmer' | 'admin') => User;
  logout: () => void;
  updateUserLocal: (patch: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const USER_CACHE_KEY = 'tq_auth_user';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const raw = localStorage.getItem(USER_CACHE_KEY);
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const token = getStoredToken();
  const isDemoSession = isDemoPreviewToken(token);

  useEffect(() => {
    let active = true;
    async function hydrate() {
      const existingToken = getStoredToken();
      if (!existingToken) {
        if (active) setIsLoading(false);
        return;
      }
      if (isDemoPreviewToken(existingToken) && user) {
        if (active) setIsLoading(false);
        return;
      }
      try {
        const me = await authService.getMe();
        if (active) {
          setUser(me);
          localStorage.setItem(USER_CACHE_KEY, JSON.stringify(me));
        }
      } catch {
        if (active) {
          setStoredToken(null);
          localStorage.removeItem(USER_CACHE_KEY);
          setUser(null);
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }
    hydrate();
    return () => {
      active = false;
    };
  }, []);

  const persistSession = (tokenValue: string, nextUser: User) => {
    setStoredToken(tokenValue);
    try {
      localStorage.setItem(USER_CACHE_KEY, JSON.stringify(nextUser));
    } catch {
      // Ignore storage error
    }
    setUser(nextUser);
  };

  const login = async (payload: LoginPayload, demoRoleHint?: 'farmer' | 'admin') => {
    const session = await authService.login(payload, demoRoleHint);
    persistSession(session.access_token, session.user);
    return session.user;
  };

  const register = async (payload: RegisterPayload) => {
    const session = await authService.register(payload);
    persistSession(session.access_token, session.user);
    return session.user;
  };

  const enterDemoSandbox = (role: 'farmer' | 'admin') => {
    const demoEmail =
      role === 'admin' ? 'admin@terraqora.demo' : 'ananya.farmer@terraqora.demo';
    const session = demoSandbox.login(demoEmail, role);
    persistSession(session.access_token, session.user);
    return session.user;
  };

  const logout = () => {
    setStoredToken(null);
    try {
      localStorage.removeItem(USER_CACHE_KEY);
    } catch {
      // Ignore
    }
    setUser(null);
  };

  const updateUserLocal = (patch: Partial<User>) => {
    setUser((prev) => {
      if (!prev) return prev;
      const updated: User = {
        ...prev,
        ...patch,
        preferred_language: (patch.preferred_language ?? prev.preferred_language) as SupportedLanguage,
      };
      try {
        localStorage.setItem(USER_CACHE_KEY, JSON.stringify(updated));
      } catch {
        // Ignore
      }
      return updated;
    });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isDemoSession,
        login,
        register,
        enterDemoSandbox,
        logout,
        updateUserLocal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
