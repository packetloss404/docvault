export interface Document {
  id: number;
  uuid: string;
  title: string;
  content: string;
  document_type: number | null;
  document_type_name: string | null;
  correspondent: number | null;
  correspondent_name: string | null;
  cabinet: number | null;
  cabinet_name: string | null;
  storage_path: number | null;
  tag_ids: number[];
  original_filename: string;
  mime_type: string;
  checksum: string;
  archive_checksum: string;
  page_count: number;
  filename: string | null;
  archive_filename: string | null;
  thumbnail_path: string;
  created: string;
  added: string;
  archive_serial_number: number | null;
  language: string;
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentType {
  id: number;
  name: string;
  slug: string;
  trash_time_period: number | null;
  trash_time_unit: string | null;
  delete_time_period: number | null;
  delete_time_unit: string | null;
  match: string;
  matching_algorithm: number;
  is_insensitive: boolean;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: number;
  version_number: number;
  comment: string;
  is_active: boolean;
  file: number | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
