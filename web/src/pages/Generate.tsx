import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  CITATION_STYLES,
  OUTPUT_FORMATS,
  PAPER_SECTIONS,
  PAPER_TYPES,
  papersApi,
  type Paper,
  type Passage,
  type Pin,
} from '../lib/api';

export const Generate: React.FC = () => {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [title, setTitle] = useState('');
  const [paperType, setPaperType] = useState('Empirical Study');
  const [citationStyle, setCitationStyle] = useState('APA');
  const [outputFormat, setOutputFormat] = useState('markdown');
  const [sections, setSections] = useState<string[]>([]);
  const [prompt, setPrompt] = useState('');
  const [passages, setPassages] = useState<Passage[]>([]);
  const [pins, setPins] = useState<Pin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!paperId) return;
    void papersApi.get(paperId).then((row) => {
      setPaper(row);
      setTitle(row.title);
      setPaperType(row.paper_type);
      setCitationStyle(row.citation_style);
      setOutputFormat(row.output_format);
      setSections(row.sections ?? []);
      setPrompt(row.research_prompt);
    });
    void papersApi.listPins(paperId).then(setPins);
  }, [paperId]);

  const persist = async (patch: Record<string, unknown>) => {
    if (!paperId) return;
    const row = await papersApi.patch(paperId, patch);
    setPaper(row);
  };

  const toggleSection = (name: string) => {
    const next = sections.includes(name) ? sections.filter((s) => s !== name) : [...sections, name];
    setSections(next);
    void persist({ sections: next });
  };

  const querySources = async () => {
    if (!paperId) return;
    if (!prompt.trim()) {
      setError('Enter a research prompt first');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await persist({ research_prompt: prompt, paper_type: paperType, sections });
      const result = await papersApi.retrieve(paperId, {
        research_prompt: prompt,
        paper_type: paperType,
        sections,
      });
      setPassages(result.passages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retrieve failed');
    } finally {
      setBusy(false);
    }
  };

  if (!paper) {
    return <p className="p-8 text-sm text-gray-600">Loading paper…</p>;
  }

  return (
    <div className="max-w-3xl mx-auto p-8 space-y-6">
      <p className="text-sm">
        <Link className="text-primary-600" to="/dashboard">
          ← Dashboard
        </Link>
      </p>
      <div className="bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-xl font-semibold">Prompt</h1>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <label className="block text-sm">
          Title
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={() => void persist({ title })}
          />
        </label>
        <label className="block text-sm">
          Paper Type
          <select
            className="mt-1 w-full border rounded px-3 py-2"
            value={paperType}
            onChange={(e) => {
              setPaperType(e.target.value);
              void persist({ paper_type: e.target.value });
            }}
          >
            {PAPER_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-sm">
            Citation Style
            <select
              className="mt-1 w-full border rounded px-3 py-2"
              value={citationStyle}
              onChange={(e) => {
                setCitationStyle(e.target.value);
                void persist({ citation_style: e.target.value });
              }}
            >
              {CITATION_STYLES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Output Format
            <select
              className="mt-1 w-full border rounded px-3 py-2"
              value={outputFormat}
              onChange={(e) => {
                setOutputFormat(e.target.value);
                void persist({ output_format: e.target.value });
              }}
            >
              {OUTPUT_FORMATS.map((t) => (
                <option key={t} value={t}>
                  {t === 'markdown' ? 'Markdown' : 'Word'}
                </option>
              ))}
            </select>
          </label>
        </div>
        <fieldset>
          <legend className="text-sm font-medium mb-2">Sections</legend>
          <div className="grid grid-cols-2 gap-1 text-sm">
            {PAPER_SECTIONS.map((name) => (
              <label key={name} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={sections.includes(name)}
                  onChange={() => toggleSection(name)}
                />
                {name}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="block text-sm">
          Research prompt
          <textarea
            className="mt-1 w-full border rounded px-3 py-2 min-h-[8rem]"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onBlur={() => void persist({ research_prompt: prompt })}
          />
        </label>
        <button
          type="button"
          disabled={busy || !prompt.trim()}
          className="bg-primary-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50"
          onClick={() => void querySources()}
        >
          {busy ? 'Retrieving…' : 'Query sources'}
        </button>
      </div>
      {pins.length ? (
        <div className="bg-white rounded shadow p-6">
          <h2 className="font-medium mb-3">Pinned ({pins.length})</h2>
          <ul className="space-y-3 text-sm">
            {pins.map((pin) => (
              <li key={pin.pin_id} className="border rounded p-3">
                <div className="flex justify-between gap-3">
                  <p className="text-xs text-gray-500">
                    {pin.source_role} · {pin.target_section || 'any section'} · {pin.file_name}
                  </p>
                  <button
                    type="button"
                    className="text-xs text-red-600"
                    onClick={() => {
                      void papersApi.unpin(paper.paper_id, pin.pin_id).then(() =>
                        papersApi.listPins(paper.paper_id).then(setPins),
                      );
                    }}
                  >
                    Unpin
                  </button>
                </div>
                <p className="mt-1">{pin.chunk_text}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {passages.length ? (
        <div className="bg-white rounded shadow p-6">
          <h2 className="font-medium mb-3">Retrieved passages ({passages.length})</h2>
          <ul className="space-y-3 text-sm">
            {passages.map((p) => {
              const pinned = pins.some((pin) => pin.vector_id === p.vector_id) || p.pinned;
              return (
                <li key={p.vector_id} className="border rounded p-3">
                  <div className="flex justify-between gap-3">
                    <p className="text-xs text-gray-500 mb-1">
                      {pinned ? 'pinned · ' : ''}
                      {p.source_role} · {p.section || 'Unknown'} · {p.chunk_role}
                    </p>
                    {pinned ? null : (
                      <button
                        type="button"
                        className="text-xs text-primary-600"
                        onClick={() => {
                          void papersApi
                            .pin(paper.paper_id, {
                              vector_id: p.vector_id,
                              file_id: p.file_id,
                            })
                            .then(() => papersApi.listPins(paper.paper_id).then(setPins));
                        }}
                      >
                        Pin
                      </button>
                    )}
                  </div>
                  <p>{p.chunk_text}</p>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
      <p className="text-xs text-gray-500">Generate and outline land in later slices.</p>
      <button type="button" className="text-sm text-gray-500" onClick={() => navigate('/dashboard')}>
        Back
      </button>
    </div>
  );
};
