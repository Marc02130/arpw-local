import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError, type LlmProvider } from '../lib/api';
import { validateFullName } from '../lib/validateAuth';

const LABELS: Record<LlmProvider, string> = {
  openai: 'OpenAI',
  xai: 'xAI (Grok)',
  anthropic: 'Anthropic (Claude)',
};

export const Profile: React.FC = () => {
  const { user, llm, refreshLlm } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [openai, setOpenai] = useState('');
  const [xai, setXai] = useState('');
  const [anthropic, setAnthropic] = useState('');
  const [provider, setProvider] = useState<LlmProvider>(llm?.chat_provider || 'xai');
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (llm) setProvider(llm.chat_provider);
  }, [llm]);

  const field = (name: LlmProvider) =>
    name === 'openai' ? openai : name === 'xai' ? xai : anthropic;
  const setField = (name: LlmProvider, value: string) => {
    if (name === 'openai') setOpenai(value);
    else if (name === 'xai') setXai(value);
    else setAnthropic(value);
  };

  const saveName = async () => {
    const nameError = validateFullName(fullName);
    if (nameError) {
      setError(nameError);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.auth.patchMe(fullName.trim());
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  };

  const saveKeys = async () => {
    setBusy(true);
    setError(null);
    setSaved(false);
    const body: Record<string, string> = { chat_provider: provider };
    if (openai.trim()) body.openai_api_key = openai.trim();
    if (xai.trim()) body.xai_api_key = xai.trim();
    if (anthropic.trim()) body.anthropic_api_key = anthropic.trim();
    try {
      await api.settings.updateLlm(body);
      setOpenai('');
      setXai('');
      setAnthropic('');
      await refreshLlm();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to save keys');
    } finally {
      setBusy(false);
    }
  };

  const clearKey = async (fieldName: 'openai_api_key' | 'xai_api_key' | 'anthropic_api_key') => {
    setBusy(true);
    setError(null);
    try {
      await api.settings.updateLlm({ [fieldName]: '' });
      await refreshLlm();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to clear key');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto p-8">
      <div className="bg-white rounded shadow p-6 space-y-8">
        <h1 className="text-xl font-semibold">Profile</h1>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        {saved ? <p className="text-sm text-green-700">Saved.</p> : null}

        <section className="space-y-3">
          <h2 className="text-sm font-medium text-gray-800">Account</h2>
          <label className="block text-sm text-gray-600">
            Email
            <input className="mt-1 w-full border rounded px-3 py-2 bg-gray-50" value={user?.email || ''} readOnly />
          </label>
          <label className="block text-sm text-gray-600">
            Full name
            <input
              className="mt-1 w-full border rounded px-3 py-2"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="bg-primary-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50"
            disabled={busy}
            onClick={() => void saveName()}
          >
            Save name
          </button>
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-medium text-gray-800">AI providers</h2>
          <p className="text-sm text-gray-600">
            Paste API keys (never shown again). Chat uses the selected provider. Uploads embed locally
            with MiniLM, so ingest does not need a cloud key.
          </p>
          {(['openai', 'xai', 'anthropic'] as const).map((name) => (
            <div key={name}>
              <label className="flex items-center justify-between text-sm font-medium text-gray-700">
                <span>
                  {LABELS[name]}
                  {llm?.[name].configured ? (
                    <span className="ml-2 text-green-700 font-normal">
                      saved (ends in …{llm[name].last4})
                    </span>
                  ) : (
                    <span className="ml-2 text-gray-400 font-normal">not set</span>
                  )}
                </span>
                {llm?.[name].configured ? (
                  <button
                    type="button"
                    className="text-xs text-red-600"
                    onClick={() => void clearKey(`${name}_api_key`)}
                  >
                    Remove
                  </button>
                ) : null}
              </label>
              <input
                type="password"
                autoComplete="off"
                placeholder={llm?.[name].configured ? '•••••••• (leave blank to keep)' : 'Paste API key'}
                className="mt-1 w-full px-3 py-2 border rounded-md text-sm"
                value={field(name)}
                onChange={(e) => setField(name, e.target.value)}
              />
            </div>
          ))}
          <fieldset>
            <legend className="text-sm font-medium text-gray-700 mb-2">Chat with</legend>
            {(['openai', 'xai', 'anthropic'] as const).map((name) => (
              <label key={name} className="flex items-center space-x-2 text-sm mb-1">
                <input
                  type="radio"
                  name="chat_provider"
                  value={name}
                  checked={provider === name}
                  onChange={() => setProvider(name)}
                />
                <span>
                  {LABELS[name]}
                  {llm?.chat_models[name] ? ` · ${llm.chat_models[name]}` : ''}
                </span>
              </label>
            ))}
          </fieldset>
          <button
            type="button"
            className="bg-primary-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50"
            disabled={busy}
            onClick={() => void saveKeys()}
          >
            Save keys
          </button>
        </section>
      </div>
    </div>
  );
};
