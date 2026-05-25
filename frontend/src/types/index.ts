export interface Document {
  id: string;
  user_id: string;
  tenant_id: string;
  filename: string;
  b2_file_key: string;
  content_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  doc_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CitationItem {
  chunk_id: string;
  page_number: number;
  heading_path: string[];
  relevance_score: number | null;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: CitationItem[];
  retrieval_metadata: Record<string, any>;
  from_cache: boolean;
  token_count: number | null;
  evaluation: EvaluationScores | null;
  created_at: string;
}

export interface EvaluationScores {
  faithfulness: number;
  groundedness: number;
  citation_accuracy: number;
  relevance: number;
}

export interface ChatSession {
  id: string;
  user_id: string;
  tenant_id: string;
  document_id: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

export interface AdminStats {
  total_users: number;
  total_documents: number;
  total_storage_bytes: number;
}

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  document_count: number;
  created_at: string;
}
