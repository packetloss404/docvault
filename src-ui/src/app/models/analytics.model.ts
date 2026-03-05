export interface SearchAnalytics {
  top_queries: { query: string; count: number; avg_results: number }[];
  zero_result_queries: { query: string; count: number }[];
  total_searches: number;
  avg_click_position: number;
  click_through_rate: number;
}

export interface SearchSynonym {
  id: number;
  terms: string[];
  enabled: boolean;
}

export interface SearchCuration {
  id: number;
  query_text: string;
  pinned_documents: number[];
  hidden_documents: number[];
  enabled: boolean;
}
