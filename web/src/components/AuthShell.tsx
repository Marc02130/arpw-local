import React from 'react';

export const AuthShell: React.FC<{ title: string; subtitle?: string; children: React.ReactNode }> = ({
  title,
  subtitle,
  children,
}) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
    <div className="w-full max-w-md bg-white shadow rounded-lg p-8">
      <img
        src="/arpw-icon.png"
        alt=""
        width={56}
        height={56}
        className="mb-4 h-14 w-14 rounded-2xl shadow-sm"
      />
      <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
      {subtitle ? <p className="mt-1 text-sm text-gray-600">{subtitle}</p> : null}
      <div className="mt-6">{children}</div>
    </div>
  </div>
);
