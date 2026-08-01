"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import DocumentLibrary from "./components/DocumentLibrary";
import ChatInterface from "./components/ChatInterface";
import SourcesPanel from "./components/SourcesPanel";
import DocumentViewerModal from "./components/DocumentViewerModal";
import { ChatMessage, DocumentOut, SourceOut } from "./lib/types";
import { deleteDocument, listDocuments, sendChatMessage, uploadDocuments } from "./lib/api";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [activeSources, setActiveSources] = useState<{ sources: SourceOut[]; grounded: boolean } | null>(null);
  const [viewerSource, setViewerSource] = useState<SourceOut | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to reach the API");
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  // Poll while any document is still processing so status flips to "ready" live.
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === "processing");
    if (hasProcessing && !pollRef.current) {
      pollRef.current = setInterval(refreshDocuments, 2500);
    }
    if (!hasProcessing && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents, refreshDocuments]);

  const handleUpload = async (files: File[]) => {
    await uploadDocuments(files);
    await refreshDocuments();
  };

  const handleDelete = async (id: string) => {
    await deleteDocument(id);
    setSelectedIds((prev) => prev.filter((x) => x !== id));
    await refreshDocuments();
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleSend = async (message: string) => {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setSending(true);
    try {
      const res = await sendChatMessage(message, conversationId, selectedIds.length ? selectedIds : null);
      setConversationId(res.conversation_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, sources: res.sources }]);
      setActiveSources({ sources: res.sources, grounded: res.grounded });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Something went wrong reaching the API: ${err instanceof Error ? err.message : "unknown error"}` },
      ]);
    } finally {
      setSending(false);
    }
  };

  const readyCount = documents.filter((d) => d.status === "ready").length;
  const chatDisabled = readyCount === 0;

  return (
    <main className="grid h-screen grid-cols-1 overflow-hidden md:grid-cols-[240px_1fr] lg:grid-cols-[280px_1fr_340px]">
      <div className="hidden md:block md:h-full md:overflow-hidden">
        <DocumentLibrary
          documents={documents}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onUpload={handleUpload}
          onDelete={handleDelete}
        />
      </div>

      <div className="flex flex-col overflow-hidden">
        {loadError && (
          <div className="border-b border-clay/40 bg-clay/10 px-4 py-2 text-center text-xs text-ink">
            Couldn't reach the API ({loadError}). Is the backend running?
          </div>
        )}
        <ChatInterface
          messages={messages}
          onSend={handleSend}
          sending={sending}
          disabled={chatDisabled}
          disabledReason="Upload and wait for a document to finish processing first"
        />
      </div>

      <div className="hidden lg:block lg:h-full lg:overflow-hidden">
        <SourcesPanel
          sources={activeSources?.sources ?? null}
          grounded={activeSources?.grounded ?? true}
          onJumpToSource={setViewerSource}
        />
      </div>

      {viewerSource && <DocumentViewerModal source={viewerSource} onClose={() => setViewerSource(null)} />}
    </main>
  );
}
