import { ChatResponse, ChunkOut, DocumentOut } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${body || res.statusText}`);
  }
  return res.json();
}

export async function uploadDocuments(files: File[]): Promise<DocumentOut[]> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form });
  return handle<DocumentOut[]>(res);
}

export async function listDocuments(): Promise<DocumentOut[]> {
  const res = await fetch(`${API_BASE}/documents`, { cache: "no-store" });
  return handle<DocumentOut[]>(res);
}

export async function getDocumentChunks(documentId: string): Promise<ChunkOut[]> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/chunks`, { cache: "no-store" });
  return handle<ChunkOut[]>(res);
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete document (${res.status})`);
}

export async function sendChatMessage(
  message: string,
  conversationId: string | null,
  documentIds: string[] | null
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      document_ids: documentIds,
    }),
  });
  return handle<ChatResponse>(res);
}
