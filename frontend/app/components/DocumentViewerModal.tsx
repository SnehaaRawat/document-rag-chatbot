"use client";

import { useEffect, useRef, useState } from "react";
import { ChunkOut, SourceOut } from "../lib/types";
import { getDocumentChunks } from "../lib/api";

interface Props {
  source: SourceOut;
  onClose: () => void;
}

export default function DocumentViewerModal({ source, onClose }: Props) {
  const [chunks, setChunks] = useState<ChunkOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getDocumentChunks(source.document_id)
      .then((data) => {
        if (!cancelled) setChunks(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [source.document_id]);

  useEffect(() => {
    if (chunks) {
      // Scroll to the matching chunk once it's rendered.
      requestAnimationFrame(() => {
        activeRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
      });
    }
  }, [chunks]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4" role="dialog" aria-modal="true">
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-lg bg-paper shadow-xl">
        <div className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div className="min-w-0">
            <h3 className="truncate font-serif text-base font-semibold text-ink">{source.document_filename}</h3>
            {source.page_number && <p className="text-xs text-inkfaint">Jumped to page {source.page_number}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded px-2 py-1 text-sm text-inkfaint hover:bg-paperdim hover:text-ink"
            aria-label="Close document viewer"
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          {!chunks && !error && <p className="text-sm text-inkfaint">Loading document…</p>}
          {chunks && (
            <div className="space-y-4">
              {chunks.map((c) => {
                const isActive = c.id === source.chunk_id;
                return (
                  <div
                    key={c.id}
                    ref={isActive ? activeRef : undefined}
                    className={`rounded-md px-3 py-2.5 ${
                      isActive ? "bg-mosslight ring-1 ring-moss" : ""
                    }`}
                  >
                    <div className="mb-1 font-mono text-[11px] uppercase tracking-wide text-inkfaint">
                      Chunk {c.chunk_index + 1}
                      {c.page_number ? ` · p.${c.page_number}` : ""}
                      {c.section_title ? ` · ${c.section_title}` : ""}
                    </div>
                    <p className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-ink">{c.content}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
