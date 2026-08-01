export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentOut {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
  chunk_count: number;
  created_at: string;
}

export interface ChunkOut {
  id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  section_title: string | null;
  token_count: number;
}

export interface SourceOut {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  content: string;
  page_number: number | null;
  section_title: string | null;
  similarity: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  sources: SourceOut[];
  grounded: boolean;
}
