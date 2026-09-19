import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { papersApi, type Passage } from '../lib/api';

const OPTIONS = [
  { id: 'literature', label: 'Supporting papers (literature)' },
  { id: 'primary', label: 'Original research' },
  { id: 'examples', label: 'Style examples (Q&A only, not pinable)' },
] as const;

export const Interrogate: React.FC = () => {
  const { paperId } = useParams<{ paperId: string }>();
  const [question, setQuestion] = useState('');
  const [sources, setSources] = useState<string[]>(['literature']);
  const [turns, setTurns] = useState<Array<{ role: string; content: string; passages?: Passage[] }>>([]);
  const [lastPassages, setLastPassages] = useState<Passage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!paperId) return;
    void papersApi.interrogation(paperId).then(setTurns);
  }, [paperId]);

  const toggle = (id: string) => {
    setSources((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  };

  const ask = async () => {
    if (!paperId || !question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await papersApi.ask(paperId, question.trim(), sources.length ? sources : ['literature']);
      setLastPassages(result.passages);
      setTurns((prev) => [
        ...prev,
        { role: 'user', content: question.trim() },
        { role: 'assistant', content: result.answer, passages: result.passages },
      ]);
      setQuestion('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Interrogate failed');
    } finally {
      setBusy(false);
    }
  };

  if (!paperId) return null;

  return (
    <div className="max-w-3xl mx-auto p-8 space-y-6">
      <p className="text-sm flex gap-4">
        <Link className="text-primary-600" to="/dashboard">
          ← Dashboard
        </Link>
        <Link className="text-primary-600" to={`/generate/${paperId}`}>
          Prompt
        </Link>
        <span className="font-medium">Interrogate</span>
      </p>
      <div className="bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-xl font-semibold">Interrogate</h1>
        <p className="text-sm text-gray-600">
          Ask your supporting papers. Include original research or style examples if you need them —
          you already know those.
        </p>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <div className="space-y-1 text-sm">
          {OPTIONS.map((opt) => (
            <label key={opt.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={sources.includes(opt.id)}
                onChange={() => toggle(opt.id)}
              />
              {opt.label}
            </label>
          ))}
        </div>
        <textarea
          className="w-full border rounded px-3 py-2 min-h-[6rem]"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question of the corpus"
        />
        <button
          type="button"
          disabled={busy || !question.trim()}
          className="bg-primary-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50"
          onClick={() => void ask()}
        >
          {busy ? 'Asking…' : 'Ask'}
        </button>
      </div>
      <div className="space-y-3">
        {turns.map((turn, i) => (
          <div key={i} className="bg-white rounded shadow p-4 text-sm">
            <p className="text-xs text-gray-500 mb-1">{turn.role}</p>
            <p className="whitespace-pre-wrap">{turn.content}</p>
          </div>
        ))}
      </div>
      {lastPassages.length ? (
        <div className="bg-white rounded shadow p-6">
          <h2 className="font-medium mb-3">Passages</h2>
          <ul className="space-y-3 text-sm">
            {lastPassages.map((p) => (
              <li key={p.vector_id} className="border rounded p-3">
                <div className="flex justify-between gap-3">
                  <p className="text-xs text-gray-500">
                    {p.source_role} · {p.section || 'Unknown'}
                  </p>
                  {p.source_role === 'example' ? null : (
                    <button
                      type="button"
                      className="text-xs text-primary-600"
                      onClick={() => {
                        void papersApi.pin(paperId, {
                          vector_id: p.vector_id,
                          file_id: p.file_id,
                        });
                      }}
                    >
                      Pin
                    </button>
                  )}
                </div>
                <p className="mt-1">{p.chunk_text}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
};
