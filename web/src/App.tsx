import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './pages/Login';
import { VerifyEmail } from './pages/VerifyEmail';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { Dashboard } from './pages/Dashboard';
import { Profile } from './pages/Profile';
import { Layout } from './components/Layout';

const Gate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading, isEmailConfirmed } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }
  if (user && !isEmailConfirmed) {
    return <Navigate to="/verify-email" replace />;
  }
  if (!user || !isEmailConfirmed) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const Shell: React.FC = () => {
  const { user, loading, isEmailConfirmed } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }
  const canUseApp = Boolean(user && isEmailConfirmed);

  return (
    <Routes>
      <Route path="/login" element={canUseApp ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route
        path="/forgot-password"
        element={canUseApp ? <Navigate to="/dashboard" replace /> : <ForgotPassword />}
      />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/verify-email"
        element={canUseApp ? <Navigate to="/dashboard" replace /> : <VerifyEmail />}
      />
      <Route
        path="/dashboard"
        element={
          <Gate>
            <Layout>
              <Dashboard />
            </Layout>
          </Gate>
        }
      />
      <Route
        path="/profile"
        element={
          <Gate>
            <Layout>
              <Profile />
            </Layout>
          </Gate>
        }
      />
      <Route path="/" element={<Navigate to={canUseApp ? '/dashboard' : '/login'} replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export const App: React.FC = () => (
  <AuthProvider>
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  </AuthProvider>
);
