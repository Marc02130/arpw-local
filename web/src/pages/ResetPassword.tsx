import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthShell } from '../components/AuthShell';
import { validateConfirmPassword, validatePassword } from '../lib/validateAuth';

export const ResetPassword: React.FC = () => {
  const { resetPassword } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!token) {
    return (
      <AuthShell title="Reset password">
        <p className="text-sm text-gray-700">This reset link is invalid or has expired.</p>
        <p className="mt-4 text-sm">
          <Link className="text-primary-600" to="/forgot-password">
            Request a new link
          </Link>
        </p>
      </AuthShell>
    );
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const passwordError = validatePassword(password);
    const confirmError = validateConfirmPassword(password, confirmPassword);
    if (passwordError || confirmError) {
      setError(passwordError || confirmError || null);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Choose a new password">
      <form className="space-y-4" onSubmit={(e) => void onSubmit(e)}>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <label className="block text-sm">
          New password
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        </label>
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
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-primary-600 text-white rounded py-2"
        >
          Save password
        </button>
      </form>
    </AuthShell>
  );
};
