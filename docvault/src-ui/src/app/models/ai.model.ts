export interface SemanticSearchResult {
  id: number;
  title: string;
  correspondent: string | null;
  document_type: string | null;
  tags: string[];
  created: string | null;
  score: number;
  hybrid_score?: number;
}

export interface SemanticSearchResponse {
  results: SemanticSearchResult[];
  count: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  question: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}

export interface ChatSource {
  document_id: number;
  title: string;
  score?: number;
  chunk_count?: number;
}

export interface SummaryResponse {
  summary: string | null;
  error?: string;
}

export interface EntityResponse {
  entities: Record<string, string[]> | null;
  error?: string;
}

export interface TitleSuggestion {
  suggested_title: string | null;
  error?: string;
}

export interface AIConfig {
  llm_enabled: boolean;
  llm_provider: string;
  llm_model: string;
  embedding_model: string;
  vector_store_count: number;
}

export interface AIStatus {
  llm_enabled: boolean;
  llm_provider: string;
  llm_model: string;
  embedding_model: string;
  vector_store_count: number;
  llm_available: boolean;
}
