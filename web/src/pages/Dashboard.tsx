import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { documentsApi, PAPER_TYPES, papersApi, type ExampleFile, type Paper, type ReferenceFile } from '../lib/api';
import { UploadZone } from '../components/UploadZone';

function statusLabel(status: string, chunks: number): string {
  if (status === 'ready') return `Indexed (${chunks} chunks)`;
  if (status === 'processing') return 'Indexing…';
  return 'Stored (not indexed)';
}

export const Dashboard: React.FC = () => {
  const { user, llm } = useAuth();
  const navigate = useNavigate();
  const [references, setReferences] = useState<ReferenceFile[]>([]);
  const [examples, setExamples] = useState<ExampleFile[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [title, setTitle] = useState('');
  const [paperType, setPaperType] = useState('Empirical Study');

  const reload = useCallback(() => {
    void documentsApi.listReferences().then(setReferences);
    void documentsApi.listExamples().then(setExamples);
    void papersApi.list().then(setPapers);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const literature = references.filter((r) => r.source_role === 'literature');
  const primary = references.filter((r) => r.source_role === 'primary');

  return (
    <div className="max-w-3xl mx-auto p-8 space-y-8">
      <div className="bg-white rounded shadow p-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-600">Signed in as {user?.email}</p>
        <p className="mt-2 text-sm text-gray-500">
          Chat provider: {llm?.chat_provider ?? 'not loaded'}. Keys live on{' '}
          <Link className="text-primary-600" to="/profile">
            Profile
          </Link>
          .
        </p>
        {llm && !(llm.openai.configured || llm.xai.configured || llm.anthropic.configured) ? (
          <p className="mt-2 text-sm text-amber-800">
            No chat key saved. Paste one on Profile before interrogate or generate. Uploads still work.
          </p>
        ) : null}
      </div>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Start a paper</h2>
        <div className="flex flex-wrap gap-2">
          <input
            className="border rounded px-3 py-2 flex-1 min-w-[12rem]"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <select
            className="border rounded px-3 py-2"
            value={paperType}
            onChange={(e) => setPaperType(e.target.value)}
          >
            {PAPER_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="bg-primary-600 text-white rounded px-4 py-2 text-sm"
            onClick={() => {
              void papersApi.create(title, paperType).then((paper) => {
                navigate(`/generate/${paper.paper_id}`);
              });
            }}
          >
            Start paper
          </button>
        </div>
        {papers.length ? (
          <ul className="text-sm divide-y">
            {papers.map((p) => (
              <li key={p.paper_id} className="py-2 flex justify-between gap-3">
                <span>
                  {p.title} · {p.paper_type} · v{p.version}
                </span>
                <span className="flex gap-2">
                  <Link className="text-primary-600" to={`/generate/${p.paper_id}`}>
                    Continue
                  </Link>
                  <button
                    type="button"
                    className="text-red-600 text-xs"
                    aria-label={`Delete ${p.title}`}
                    onClick={() => {
                      if (!window.confirm(`Delete “${p.title}”?`)) return;
                      void papersApi.remove(p.paper_id).then(reload);
                    }}
                  >
                    Delete
                  </button>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No drafts yet. Start a paper above.</p>
        )}
      </section>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Supporting papers (literature) · {literature.length}/500</h2>
        <UploadZone kind="literature" existingCount={literature.length} cap={500} onChanged={reload} />
        <FileList
          rows={literature}
          empty="No supporting papers yet. Drop a pdf, docx, or txt to index."
          onDelete={(id) => void documentsApi.deleteReference(id).then(reload)}
        />
      </section>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Original research (primary) · {primary.length}/100</h2>
        <UploadZone kind="primary" existingCount={primary.length} cap={100} onChanged={reload} />
        <FileList
          rows={primary}
          empty="No original-research files yet. Optional for literature reviews."
          onDelete={(id) => void documentsApi.deleteReference(id).then(reload)}
        />
      </section>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Style examples · {examples.length}/10</h2>
        <UploadZone kind="example" existingCount={examples.length} cap={10} onChanged={reload} />
        {examples.length === 0 ? (
          <p className="text-sm text-gray-500">No style examples yet. Optional — for voice only.</p>
        ) : (
          <ul className="text-sm divide-y">
            {examples.map((row) => (
              <li key={row.file_id} className="py-2 flex justify-between gap-3">
                <span>
                  {row.file_name} · {statusLabel(row.status, row.chunk_count)}
                  {row.status === 'failed'
                    ? ` · Couldn’t parse this file. Delete it and try another format. ${row.error_message || ''}`
                    : row.error_message
                      ? ` · ${row.error_message}`
                      : ''}
                </span>
                <button
                  type="button"
                  className="text-red-600 text-xs"
                  aria-label={`Delete ${row.file_name}`}
                  onClick={() => void documentsApi.deleteExample(row.file_id).then(reload)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

const FileList: React.FC<{
  rows: ReferenceFile[];
  onDelete: (id: string) => void;
  empty: string;
}> = ({ rows, onDelete, empty }) =>
  rows.length === 0 ? (
    <p className="text-sm text-gray-500">{empty}</p>
  ) : (
    <ul className="text-sm divide-y">
      {rows.map((row) => (
        <li key={row.file_id} className="py-2 flex justify-between gap-3">
          <span>
            {row.file_name} · {statusLabel(row.status, row.chunk_count)}
            {row.status === 'failed'
              ? ` · Couldn’t parse this file. Delete it and try another format. ${row.error_message || ''}`
              : row.error_message
                ? ` · ${row.error_message}`
                : ''}
          </span>
          <button
            type="button"
            className="text-red-600 text-xs"
            aria-label={`Delete ${row.file_name}`}
            onClick={() => onDelete(row.file_id)}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
