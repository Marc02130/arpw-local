import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Dashboard: React.FC = () => {
  const { user, llm } = useAuth();
  return (
    <div className="max-w-xl mx-auto p-8">
      <div className="bg-white rounded shadow p-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-600">Signed in as {user?.email}</p>
        <p className="mt-2 text-sm text-gray-500">
          Chat provider: {llm?.chat_provider ?? 'not loaded'}. Paste keys on{' '}
          <Link className="text-primary-600" to="/profile">
            Profile
          </Link>
          .
        </p>
        <p className="mt-4 text-sm text-gray-500">Upload, generate, and library land in later slices.</p>
      </div>
    </div>
  );
};
