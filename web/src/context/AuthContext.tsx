import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, ApiError, type LlmSettings, type User } from '../lib/api';

type AuthContextValue = {
  user: User | null;
  llm: LlmSettings | null;
  loading: boolean;
  isEmailConfirmed: boolean;
  refreshLlm: () => Promise<void>;
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
  const [llm, setLlm] = useState<LlmSettings | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshLlm = useCallback(async () => {
    try {
      setLlm(await api.settings.llm());
    } catch {
      setLlm(null);
    }
  }, []);

  useEffect(() => {
    api.auth
      .me()
      .then(async (me) => {
        setUser(me);
        if (me.email_confirmed_at) {
          await refreshLlm();
        }
      })
      .catch(() => {
        setUser(null);
        setLlm(null);
      })
      .finally(() => setLoading(false));

    const onUnauthorized = () => {
      setUser(null);
      setLlm(null);
    };
    window.addEventListener('arpw:unauthorized', onUnauthorized);
    return () => window.removeEventListener('arpw:unauthorized', onUnauthorized);
  }, [refreshLlm]);

  const login = useCallback(async (email: string, password: string) => {
    const me = await api.auth.login(email, password);
    setUser(me);
    if (me.email_confirmed_at) {
      await refreshLlm();
    }
  }, [refreshLlm]);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await api.auth.register(email, password, fullName);
    setUser(null);
    setLlm(null);
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
    setLlm(null);
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
    if (me.email_confirmed_at) {
      await refreshLlm();
    }
  }, [refreshLlm]);

  const isEmailConfirmed = Boolean(user?.email_confirmed_at);

  const value = useMemo(
    () => ({
      user,
      llm,
      loading,
      isEmailConfirmed,
      refreshLlm,
      login,
      register,
      logout,
      resendConfirmation,
      forgotPassword,
      resetPassword,
    }),
    [
      user,
      llm,
      loading,
      isEmailConfirmed,
      refreshLlm,
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
