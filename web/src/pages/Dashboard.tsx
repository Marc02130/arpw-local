import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { documentsApi, type ExampleFile, type ReferenceFile } from '../lib/api';
import { UploadZone } from '../components/UploadZone';

function statusLabel(status: string, chunks: number): string {
  if (status === 'ready') return `Indexed (${chunks} chunks)`;
  if (status === 'processing') return 'Indexing…';
  return 'Stored (not indexed)';
}

export const Dashboard: React.FC = () => {
  const { user, llm } = useAuth();
  const [references, setReferences] = useState<ReferenceFile[]>([]);
  const [examples, setExamples] = useState<ExampleFile[]>([]);

  const reload = useCallback(() => {
    void documentsApi.listReferences().then(setReferences);
    void documentsApi.listExamples().then(setExamples);
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
      </div>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Supporting papers (literature) · {literature.length}/500</h2>
        <UploadZone kind="literature" existingCount={references.length} cap={500} onChanged={reload} />
        <FileList
          rows={literature}
          onDelete={(id) => void documentsApi.deleteReference(id).then(reload)}
        />
      </section>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Original research (primary) · {primary.length} of the 500 reference slots</h2>
        <UploadZone kind="primary" existingCount={references.length} cap={500} onChanged={reload} />
        <FileList
          rows={primary}
          onDelete={(id) => void documentsApi.deleteReference(id).then(reload)}
        />
      </section>

      <section className="bg-white rounded shadow p-6 space-y-3">
        <h2 className="font-medium">Style examples · {examples.length}/10</h2>
        <UploadZone kind="example" existingCount={examples.length} cap={10} onChanged={reload} />
        <ul className="text-sm divide-y">
          {examples.map((row) => (
            <li key={row.file_id} className="py-2 flex justify-between gap-3">
              <span>
                {row.file_name} · {statusLabel(row.status, row.chunk_count)}
                {row.error_message ? ` · ${row.error_message}` : ''}
              </span>
              <button
                type="button"
                className="text-red-600 text-xs"
                onClick={() => void documentsApi.deleteExample(row.file_id).then(reload)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

const FileList: React.FC<{
  rows: ReferenceFile[];
  onDelete: (id: string) => void;
}> = ({ rows, onDelete }) => (
  <ul className="text-sm divide-y">
    {rows.map((row) => (
      <li key={row.file_id} className="py-2 flex justify-between gap-3">
        <span>
          {row.file_name} · {statusLabel(row.status, row.chunk_count)}
          {row.error_message ? ` · ${row.error_message}` : ''}
        </span>
        <button type="button" className="text-red-600 text-xs" onClick={() => onDelete(row.file_id)}>
          Delete
        </button>
      </li>
    ))}
  </ul>
);
