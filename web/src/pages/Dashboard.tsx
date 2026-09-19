import React from 'react';
import { useAuth } from '../context/AuthContext';

export const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-xl mx-auto bg-white rounded shadow p-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-600">Signed in as {user?.email}</p>
        <p className="mt-4 text-sm text-gray-500">Upload, generate, and library land in later slices.</p>
        <button type="button" className="mt-6 text-primary-600" onClick={() => void logout()}>
          Sign out
        </button>
      </div>
    </div>
  );
};
