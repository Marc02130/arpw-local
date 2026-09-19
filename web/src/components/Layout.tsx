import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api, type LlmProvider } from '../lib/api';

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, llm, logout, refreshLlm } = useAuth();
  const navigate = useNavigate();

  const onProvider = async (provider: LlmProvider) => {
    await api.settings.updateLlm({ chat_provider: provider });
    await refreshLlm();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between gap-4">
        <nav className="flex items-center gap-4 text-sm">
          <Link className="font-semibold text-gray-900" to="/dashboard">
            ARPW
          </Link>
          <Link className="text-gray-600 hover:text-gray-900" to="/dashboard">
            Dashboard
          </Link>
          <Link className="text-gray-600 hover:text-gray-900" to="/profile">
            Profile
          </Link>
        </nav>
        <div className="flex items-center gap-3 text-sm">
          {llm ? (
            <label className="flex items-center gap-2 text-gray-600">
              Chat
              <select
                className="border rounded px-2 py-1"
                value={llm.chat_provider}
                onChange={(e) => void onProvider(e.target.value as LlmProvider)}
              >
                <option value="openai" disabled={!llm.openai.configured}>
                  OpenAI
                </option>
                <option value="xai" disabled={!llm.xai.configured}>
                  xAI
                </option>
                <option value="anthropic" disabled={!llm.anthropic.configured}>
                  Anthropic
                </option>
              </select>
            </label>
          ) : null}
          <span className="text-gray-500">{user?.email}</span>
          <button
            type="button"
            className="text-primary-600"
            onClick={() => {
              void logout().then(() => navigate('/login'));
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      {children}
    </div>
  );
};
