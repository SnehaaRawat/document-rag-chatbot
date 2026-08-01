"use client";

import { SourceOut } from "../lib/types";

interface Props {
  sources: SourceOut[] | null;
  grounded: boolean;
  onJumpToSource: (source: SourceOut) => void;
}

export default function SourcesPanel({ sources, grounded, onJumpToSource }: Props) {
  return (
    <aside className="flex h-full w-full flex-col border-l border-rule bg-paperdim">
      <div className="border-b border-rule px-5 py-4">
        <h2 className="font-serif text-base font-semibold text-ink">Sources</h2>
        <p className="mt-0.5 text-xs text-inkfaint">Passages the answer was grounded in</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {!sources && (
          <p className="text-sm text-inkfaint">Ask a question — the passages used to answer it will appear here.</p>
        )}

        {sources && sources.length === 0 && !grounded && (
          <div className="rounded-md border border-clay/40 bg-clay/10 px-3 py-2.5 text-sm text-ink">
            No passage cleared the similarity threshold, so no sources were used for that answer.
          </div>
        )}

        {sources && sources.length > 0 && (
          <ul className="space-y-3">
            {sources.map((s, i) => {
              const pct = Math.max(0, Math.min(100, Math.round(s.similarity * 100)));
              return (
                <li key={s.chunk_id}>
                  <button
                    type="button"
                    onClick={() => onJumpToSource(s)}
                    className="w-full rounded-md border border-rule bg-paper px-3 py-2.5 text-left transition-colors hover:border-moss"
                  >
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="truncate font-mono text-[11px] uppercase tracking-wide text-inkfaint">
                        {i + 1} · {s.document_filename}
                        {s.page_number ? ` · p.${s.page_number}` : ""}
                      </span>
                      <span className="shrink-0 font-mono text-[11px] text-moss">{pct}%</span>
                    </div>
                    <div className="ink-bar mb-2">
                      <span style={{ width: `${pct}%` }} />
                    </div>
                    {s.section_title && (
                      <p className="mb-1 text-xs font-medium text-clay">{s.section_title}</p>
                    )}
                    <p className="line-clamp-4 font-serif text-sm leading-relaxed text-ink">{s.content}</p>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
