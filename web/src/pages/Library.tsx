import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { documentsApi, papersApi, type Paper, type ReferenceFile } from '../lib/api';
import {
  DRAFT_DISCLAIMER,
  checksExportBlock,
  downloadTextFile,
  exportFileName,
  paperToMarkdown,
} from '../lib/exportPaper';

const PAGE = 25;

export const Library: React.FC = () => {
  const navigate = useNavigate();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sources, setSources] = useState<ReferenceFile[]>([]);
  const [page, setPage] = useState(1);
  const [sourcePage, setSourcePage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const reload = () => {
    void papersApi.list().then(setPapers);
    void documentsApi.listReferences().then(setSources);
  };

  useEffect(() => {
    reload();
  }, []);

  const grouped = useMemo(() => {
    const order: string[] = [];
    const map = new Map<string, Paper[]>();
    for (const paper of papers) {
      const list = map.get(paper.title);
      if (!list) {
        map.set(paper.title, [paper]);
        order.push(paper.title);
      } else {
        list.push(paper);
      }
    }
    return order.map((title) => ({
      title,
      versions: (map.get(title) ?? []).slice().sort((a, b) => b.version - a.version),
    }));
  }, [papers]);

  const pageCount = Math.max(1, Math.ceil(grouped.length / PAGE));
  const shown = grouped.slice((page - 1) * PAGE, page * PAGE);
  const sourceCount = Math.max(1, Math.ceil(sources.length / PAGE));
  const shownSources = sources.slice((sourcePage - 1) * PAGE, sourcePage * PAGE);

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <h1 className="text-xl font-semibold">Library</h1>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <section className="bg-white rounded shadow p-6">
        <h2 className="font-medium mb-3">Papers</h2>
        {shown.length === 0 ? (
          <p className="text-sm text-gray-500">No drafts yet.</p>
        ) : (
          <ul className="divide-y text-sm">
            {shown.map(({ title, versions }) => {
              const latest = versions[0];
              return (
                <li key={title} className="py-3 space-y-2">
                  <div className="flex flex-wrap justify-between gap-2">
                    <div>
                      <p className="font-medium">{latest.title}</p>
                      <p className="text-xs text-gray-500">
                        {latest.paper_type} · v{latest.version} · {latest.status} · {latest.citation_style}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link className="text-primary-600" to={`/generate/${latest.paper_id}`}>
                        Continue
                      </Link>
                      <button
                        type="button"
                        className="text-primary-600"
                        onClick={() => {
                          void papersApi.regenerate(latest.paper_id).then((row) => {
                            navigate(`/generate/${row.paper_id}`);
                          });
                        }}
                      >
                        Regenerate
                      </button>
                      <button
                        type="button"
                        className="text-primary-600"
                        onClick={() => {
                          const md = paperToMarkdown(
                            { title: latest.title, content: latest.content, version: latest.version },
                            { checks: checksExportBlock([]), disclaimer: DRAFT_DISCLAIMER },
                          );
                          downloadTextFile(md, exportFileName(latest.title, latest.version, 'md'), 'text/markdown');
                        }}
                      >
                        Markdown
                      </button>
                      <button
                        type="button"
                        className="text-primary-600"
                        onClick={() => {
                          void fetch(`/api/papers/${latest.paper_id}/export.docx`, {
                            credentials: 'include',
                          }).then(async (res) => {
                            if (!res.ok) throw new Error('Export failed');
                            const blob = await res.blob();
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = exportFileName(latest.title, latest.version, 'docx');
                            a.click();
                            URL.revokeObjectURL(url);
                          });
                        }}
                      >
                        Word
                      </button>
                      <button
                        type="button"
                        className="text-red-600"
                        aria-label={`Delete ${latest.title}`}
                        onClick={() => {
                          if (!window.confirm(`Delete “${latest.title}” v${latest.version}?`)) return;
                          void papersApi.remove(latest.paper_id).then(reload);
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  {versions.length > 1 ? (
                    <p className="text-xs text-gray-500">
                      Versions:{' '}
                      {versions.map((v) => (
                        <Link key={v.paper_id} className="mr-2 text-primary-600" to={`/generate/${v.paper_id}`}>
                          v{v.version}
                        </Link>
                      ))}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
        {grouped.length > PAGE ? (
          <div className="mt-3 flex gap-2 text-sm">
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Prev
            </button>
            <span>
              {page} / {pageCount}
            </span>
            <button type="button" disabled={page >= pageCount} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        ) : null}
      </section>

      <section className="bg-white rounded shadow p-6">
        <h2 className="font-medium mb-3">Source citations</h2>
        {shownSources.length === 0 ? (
          <p className="text-sm text-gray-500">No references uploaded.</p>
        ) : (
          <ul className="space-y-4 text-sm">
            {shownSources.map((src) => (
              <CitationRow key={src.file_id} src={src} onSaved={reload} onError={setError} />
            ))}
          </ul>
        )}
        {sources.length > PAGE ? (
          <div className="mt-3 flex gap-2 text-sm">
            <button type="button" disabled={sourcePage <= 1} onClick={() => setSourcePage((p) => p - 1)}>
              Prev
            </button>
            <span>
              {sourcePage} / {sourceCount}
            </span>
            <button
              type="button"
              disabled={sourcePage >= sourceCount}
              onClick={() => setSourcePage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
};

const CitationRow: React.FC<{
  src: ReferenceFile;
  onSaved: () => void;
  onError: (msg: string | null) => void;
}> = ({ src, onSaved, onError }) => {
  const [text, setText] = useState(src.citation_text || '');
  useEffect(() => {
    setText(src.citation_text || '');
  }, [src.citation_text]);
  return (
    <li className="border rounded p-3 space-y-2">
      <p className="font-medium">
        {src.file_name} · {src.source_role}
      </p>
      <textarea
        className="w-full border rounded px-2 py-1 min-h-[4rem]"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="flex gap-2">
        <button
          type="button"
          className="text-primary-600"
          onClick={() => {
            onError(null);
            void documentsApi
              .patchReference(src.file_id, { citation_text: text })
              .then(onSaved)
              .catch((err) => onError(err instanceof Error ? err.message : 'Save failed'));
          }}
        >
          Save citation
        </button>
        <button
          type="button"
          className="text-primary-600"
          onClick={() => {
            onError(null);
            void documentsApi
              .lookupCitation(src.file_id)
              .then(onSaved)
              .catch((err) => onError(err instanceof Error ? err.message : 'Lookup failed'));
          }}
        >
          Lookup DOI
        </button>
      </div>
    </li>
  );
};
