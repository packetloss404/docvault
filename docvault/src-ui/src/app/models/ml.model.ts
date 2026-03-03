export interface SuggestionItem {
  id: number;
  confidence: number;
  name?: string;
}

export interface Suggestions {
  tags: SuggestionItem[];
  correspondent: SuggestionItem[];
  document_type: SuggestionItem[];
  storage_path: SuggestionItem[];
}

export interface ClassifierStatus {
  available: boolean;
  format_version?: number;
  tags_trained: boolean;
  correspondent_trained: boolean;
  document_type_trained: boolean;
  storage_path_trained: boolean;
  tags_data_hash?: string;
  correspondent_data_hash?: string;
  document_type_data_hash?: string;
  storage_path_data_hash?: string;
}
