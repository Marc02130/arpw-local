import React, { useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthShell } from '../components/AuthShell';

export const VerifyEmail: React.FC = () => {
  const { resendConfirmation } = useAuth();
  const location = useLocation();
  const [params] = useSearchParams();
  const email = useMemo(() => {
    return (location.state as { email?: string } | null)?.email || '';
  }, [location.state]);
  const invalid = params.get('error') === 'invalid';
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const onResend = async () => {
    if (!email) return;
    setBusy(true);
    await resendConfirmation(email);
    setBusy(false);
    setSent(true);
  };

  return (
    <AuthShell title="Check your email" subtitle="Confirm your address before you can use the app">
      {invalid ? (
        <p className="text-sm text-red-600 mb-4">This confirmation link is invalid or has expired.</p>
      ) : null}
      {sent ? (
        <p className="text-sm text-green-700 mb-4">Confirmation email sent{email ? ` to ${email}` : ''}.</p>
      ) : null}
      <p className="text-sm text-gray-700">
        We sent a verification link{email ? ` to ${email}` : ''}. Until you confirm, you cannot sign in.
      </p>
      <p className="text-sm text-gray-500 mt-3">
        Local mailbox:{' '}
        <a className="text-primary-600" href="http://localhost:8026" target="_blank" rel="noreferrer">
          http://localhost:8026
        </a>
      </p>
      <button
        type="button"
        className="mt-4 w-full border rounded py-2 disabled:opacity-50"
        disabled={!email || busy}
        onClick={() => void onResend()}
      >
        Resend confirmation
      </button>
      <p className="mt-4 text-sm">
        <Link className="text-primary-600" to="/login">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
};
