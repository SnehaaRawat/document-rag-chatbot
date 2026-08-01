"use client";

import { useCallback, useRef, useState } from "react";
import { DocumentOut } from "../lib/types";

interface Props {
  documents: DocumentOut[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onUpload: (files: File[]) => Promise<void>;
  onDelete: (id: string) => void;
}

const statusLabel: Record<string, string> = {
  processing: "Processing…",
  ready: "Ready",
  failed: "Failed",
};

const statusDot: Record<string, string> = {
  processing: "bg-clay animate-pulse",
  ready: "bg-moss",
  failed: "bg-red-500",
};

export default function DocumentLibrary({ documents, selectedIds, onToggleSelect, onUpload, onDelete }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      setUploading(true);
      try {
        await onUpload(Array.from(fileList));
      } finally {
        setUploading(false);
      }
    },
    [onUpload]
  );

  return (
    <aside className="flex h-full w-full flex-col border-r border-rule bg-paper">
      <div className="border-b border-rule px-5 py-4">
        <h1 className="font-serif text-lg font-semibold text-ink">Marginal</h1>
        <p className="mt-0.5 text-xs text-inkfaint">Document RAG chat, cited every time</p>
      </div>

      <div className="px-4 pt-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={`w-full rounded-md border border-dashed px-4 py-6 text-center text-sm transition-colors ${
            dragOver ? "border-moss bg-mosslight text-moss" : "border-rule text-inkfaint hover:border-moss/60 hover:text-ink"
          }`}
        >
          {uploading ? "Uploading…" : "Drop a document, or click to browse"}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.md,.docx,.pptx,.csv,.xlsx,.xls,.html,.htm,.png,.jpg,.jpeg,.webp"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </button>
        <p className="mt-1.5 text-center text-[11px] text-inkfaint">
          PDF, Word, PowerPoint, Excel/CSV, HTML, Markdown, text, or images
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-inkfaint">
          Library {documents.length > 0 && `(${documents.length})`}
        </h2>
        {documents.length === 0 && (
          <p className="text-sm text-inkfaint">No documents yet. Upload one to start asking questions.</p>
        )}
        <ul className="space-y-1.5">
          {documents.map((doc) => {
            const selected = selectedIds.includes(doc.id);
            return (
              <li key={doc.id}>
                <div
                  className={`group flex items-start gap-2 rounded-md border px-3 py-2 text-sm transition-colors ${
                    selected ? "border-moss bg-mosslight" : "border-transparent hover:bg-paperdim"
                  }`}
                >
                  <button
                    type="button"
                    disabled={doc.status !== "ready"}
                    onClick={() => onToggleSelect(doc.id)}
                    className="flex flex-1 items-start gap-2 text-left disabled:cursor-not-allowed"
                    title={doc.status === "ready" ? "Include in chat scope" : statusLabel[doc.status]}
                  >
                    <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${statusDot[doc.status]}`} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-ink">{doc.filename}</span>
                      <span className="block text-xs text-inkfaint">
                        {statusLabel[doc.status]}
                        {doc.status === "ready" && doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
                        {doc.status === "failed" && doc.error_message ? ` · ${doc.error_message}` : ""}
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(doc.id)}
                    className="shrink-0 text-inkfaint opacity-0 transition-opacity hover:text-ink group-hover:opacity-100"
                    aria-label={`Remove ${doc.filename}`}
                  >
                    ✕
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="border-t border-rule px-4 py-3 text-xs text-inkfaint">
        {selectedIds.length === 0
          ? "Chatting across all ready documents"
          : `Scoped to ${selectedIds.length} selected document${selectedIds.length > 1 ? "s" : ""}`}
      </div>
    </aside>
  );
}
