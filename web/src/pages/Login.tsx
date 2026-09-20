import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthShell } from '../components/AuthShell';
import { ApiError } from '../lib/api';
import { validateLoginFields } from '../lib/validateAuth';

export const Login: React.FC = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [signUp, setSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const fieldErrors = validateLoginFields(
      { email, password, confirmPassword, fullName },
      signUp,
    );
    const first = Object.values(fieldErrors)[0];
    if (first) {
      setError(first);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (signUp) {
        await register(email, password, fullName);
        navigate('/verify-email', { state: { email } });
      } else {
        await login(email, password);
        navigate('/dashboard');
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === 'email_not_confirmed') {
        navigate('/verify-email', { state: { email } });
        return;
      }
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title={signUp ? 'Create an account' : 'Sign in'}
      subtitle="AI Research Paper Writer"
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        {signUp ? (
          <label className="block text-sm">
            Full name
            <input
              className="mt-1 w-full border rounded px-3 py-2"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="name"
            />
          </label>
        ) : null}
        <label className="block text-sm" htmlFor="email">
          Email
          <input
            id="email"
            className="mt-1 w-full border rounded px-3 py-2"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>
        <label className="block text-sm" htmlFor="password">
          Password
          <input
            id="password"
            className="mt-1 w-full border rounded px-3 py-2"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={signUp ? 'new-password' : 'current-password'}
          />
        </label>
        {signUp ? (
          <label className="block text-sm">
            Confirm password
            <input
              className="mt-1 w-full border rounded px-3 py-2"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
            />
          </label>
        ) : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-primary-600 text-white rounded py-2 disabled:opacity-50"
        >
          {busy ? 'Working…' : signUp ? 'Sign up' : 'Sign in'}
        </button>
      </form>
      <p className="mt-4 text-sm text-gray-600">
        {signUp ? (
          <button type="button" className="text-primary-600" onClick={() => setSignUp(false)}>
            Already have an account? Sign in
          </button>
        ) : (
          <>
            <button type="button" className="text-primary-600" onClick={() => setSignUp(true)}>
              Create an account
            </button>
            {' · '}
            <Link className="text-primary-600" to="/forgot-password">
              Forgot password
            </Link>
          </>
        )}
      </p>
    </AuthShell>
  );
};
