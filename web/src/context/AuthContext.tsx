import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, ApiError, type User } from '../lib/api';

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  isEmailConfirmed: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  resendConfirmation: (email: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (token: string, password: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.auth
      .me()
      .then((me) => setUser(me))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));

    const onUnauthorized = () => setUser(null);
    window.addEventListener('arpw:unauthorized', onUnauthorized);
    return () => window.removeEventListener('arpw:unauthorized', onUnauthorized);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const me = await api.auth.login(email, password);
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await api.auth.register(email, password, fullName);
    setUser(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch (err) {
      if (!(err instanceof ApiError)) {
        throw err;
      }
    }
    setUser(null);
  }, []);

  const resendConfirmation = useCallback(async (email: string) => {
    await api.auth.resendConfirmation(email);
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    await api.auth.forgotPassword(email);
  }, []);

  const resetPassword = useCallback(async (token: string, password: string) => {
    const me = await api.auth.resetPassword(token, password);
    setUser(me);
  }, []);

  const isEmailConfirmed = Boolean(user?.email_confirmed_at);

  const value = useMemo(
    () => ({
      user,
      loading,
      isEmailConfirmed,
      login,
      register,
      logout,
      resendConfirmation,
      forgotPassword,
      resetPassword,
    }),
    [
      user,
      loading,
      isEmailConfirmed,
      login,
      register,
      logout,
      resendConfirmation,
      forgotPassword,
      resetPassword,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
