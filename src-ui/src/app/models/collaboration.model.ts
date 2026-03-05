export interface Comment {
  id: number;
  document: number;
  user: number;
  username: string;
  text: string;
  created_at: string;
  updated_at: string;
}

export interface CheckoutStatus {
  checked_out: boolean;
  checkout?: CheckoutInfo;
}

export interface CheckoutInfo {
  id: number;
  document: number;
  user: number;
  username: string;
  checked_out_at: string;
  expiration: string | null;
  block_new_uploads: boolean;
  is_expired: boolean;
}

export interface ShareLink {
  id: number;
  document: number;
  document_title: string;
  slug: string;
  created_by: number;
  created_by_username: string;
  expiration: string | null;
  has_password: boolean;
  is_expired: boolean;
  file_version: string;
  download_count: number;
  created_at: string;
}

export interface ShareLinkCreateRequest {
  expiration_hours?: number | null;
  password?: string;
  file_version?: string;
}

export interface PublicShareAccess {
  document_id?: number;
  document_title: string;
  file_version?: string;
  download_count?: number;
  requires_password?: boolean;
}

export interface ActivityEntry {
  id: number;
  event_type: string;
  title: string;
  body: string;
  document_id: number | null;
  document_title: string | null;
  user: string | null;
  created_at: string;
}
