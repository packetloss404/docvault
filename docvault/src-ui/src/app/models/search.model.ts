export interface SearchResult {
  id: number;
  title: string;
  content: string;
  correspondent: string | null;
  document_type: string | null;
  tags: string[];
  created: string;
  score: number;
  highlights?: {
    title?: string[];
    content?: string[];
  };
}

export interface SearchResponse {
  count: number;
  page: number;
  page_size: number;
  results: SearchResult[];
  facets: SearchFacets;
}

export interface SearchFacets {
  tags?: FacetBucket[];
  document_types?: FacetBucket[];
  correspondents?: FacetBucket[];
  date_histogram?: FacetBucket[];
}

export interface FacetBucket {
  key: string | number;
  count: number;
}

export interface AutocompleteResult {
  id: number;
  title: string;
  correspondent: string | null;
  document_type: string | null;
  score: number;
}

export type DisplayMode = 'table' | 'small_cards' | 'large_cards';

export interface SavedView {
  id: number;
  name: string;
  display_mode: DisplayMode;
  display_fields: string[];
  sort_field: string;
  sort_reverse: boolean;
  page_size: number;
  show_on_dashboard: boolean;
  show_in_sidebar: boolean;
  filter_rules: FilterRule[];
  owner: number;
  created_at: string;
  updated_at: string;
}

export interface SavedViewListItem {
  id: number;
  name: string;
  display_mode: DisplayMode;
  show_on_dashboard: boolean;
  show_in_sidebar: boolean;
  rule_count: number;
  owner: number;
  created_at: string;
  updated_at: string;
}

export interface FilterRule {
  id?: number;
  rule_type: string;
  rule_type_display?: string;
  value: string;
}

export const FILTER_RULE_TYPES: { value: string; label: string }[] = [
  { value: 'title_contains', label: 'Title contains' },
  { value: 'content_contains', label: 'Content contains' },
  { value: 'correspondent_is', label: 'Correspondent is' },
  { value: 'document_type_is', label: 'Document type is' },
  { value: 'tag_is', label: 'Has tag' },
  { value: 'cabinet_is', label: 'Cabinet is' },
  { value: 'created_after', label: 'Created after' },
  { value: 'created_before', label: 'Created before' },
  { value: 'language_is', label: 'Language is' },
  { value: 'has_tags', label: 'Has any tags' },
  { value: 'has_no_tags', label: 'Has no tags' },
  { value: 'has_correspondent', label: 'Has a correspondent' },
  { value: 'has_no_correspondent', label: 'Has no correspondent' },
  { value: 'has_asn', label: 'Has ASN' },
  { value: 'has_no_asn', label: 'Has no ASN' },
  { value: 'filename_contains', label: 'Filename contains' },
];
