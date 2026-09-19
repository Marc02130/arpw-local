import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthShell } from '../components/AuthShell';
import { validateEmail } from '../lib/validateAuth';

export const ForgotPassword: React.FC = () => {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const emailError = validateEmail(email);
    if (emailError) {
      setError(emailError);
      return;
    }
    setBusy(true);
    setError(null);
    await forgotPassword(email);
    setBusy(false);
    setSent(true);
  };

  return (
    <AuthShell title="Forgot password">
      {sent ? (
        <p className="text-sm text-gray-700">
          If an account exists for that address, a reset link is on its way. Check{' '}
          <a className="text-primary-600" href="http://127.0.0.1:54324" target="_blank" rel="noreferrer">
            http://127.0.0.1:54324
          </a>
          .
        </p>
      ) : (
        <form className="space-y-4" onSubmit={(e) => void onSubmit(e)}>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <label className="block text-sm">
            Email
            <input
              className="mt-1 w-full border rounded px-3 py-2"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="w-full bg-primary-600 text-white rounded py-2"
          >
            Send reset link
          </button>
        </form>
      )}
      <p className="mt-4 text-sm">
        <Link className="text-primary-600" to="/login">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
};
