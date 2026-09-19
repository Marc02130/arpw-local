import React, { useCallback, useRef, useState } from 'react';
import { documentsApi, type SourceRole } from '../lib/api';

const ACCEPTED = '.pdf,.docx,.txt';
const MAX_BYTES = 10 * 1024 * 1024;
const CONCURRENCY = 10;

type Kind = 'literature' | 'primary' | 'example';

type Props = {
  kind: Kind;
  existingCount: number;
  cap: number;
  onChanged: () => void;
};

async function mapPool<T>(items: T[], limit: number, fn: (item: T) => Promise<void>) {
  const queue = [...items];
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (queue.length) {
      const next = queue.shift();
      if (next !== undefined) await fn(next);
    }
  });
  await Promise.all(workers);
}

export const UploadZone: React.FC<Props> = ({ kind, existingCount, cap, onChanged }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string[]>([]);

  const run = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      setError(null);
      if (existingCount + list.length > cap) {
        setError(
          kind === 'example'
            ? 'Example cap of 10 files reached'
            : 'Reference cap of 500 files reached',
        );
        return;
      }
      for (const file of list) {
        if (file.size <= 0 || file.size > MAX_BYTES) {
          setError(`${file.name} must be between 1 byte and 10 MB`);
          return;
        }
        if (!/\.(pdf|docx|txt)$/i.test(file.name)) {
          setError(`${file.name} must be pdf, docx, or txt`);
          return;
        }
      }
      setBusy(true);
      setProgress(list.map((f) => `${f.name}: uploading…`));
      try {
        await mapPool(list, CONCURRENCY, async (file) => {
          if (kind === 'example') {
            await documentsApi.uploadExample(file);
          } else {
            await documentsApi.uploadReference(file, kind as SourceRole);
          }
          setProgress((prev) =>
            prev.map((row) => (row.startsWith(`${file.name}:`) ? `${file.name}: indexed` : row)),
          );
        });
        onChanged();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setBusy(false);
      }
    },
    [cap, existingCount, kind, onChanged],
  );

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files) void run(e.target.files);
          e.target.value = '';
        }}
      />
      <button
        type="button"
        disabled={busy}
        className="border border-dashed rounded px-4 py-6 w-full text-sm text-gray-600 disabled:opacity-50"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (e.dataTransfer.files) void run(e.dataTransfer.files);
        }}
      >
        Drop pdf/docx/txt (max 10 MB each). No per-drop count limit; library cap is {cap}.
      </button>
      {error ? <p className="text-sm text-red-600 mt-2">{error}</p> : null}
      {progress.length ? (
        <ul className="mt-2 text-xs text-gray-500 space-y-1">
          {progress.map((row) => (
            <li key={row}>{row}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};
