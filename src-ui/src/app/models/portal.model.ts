export interface PortalConfig {
  id: number;
  name: string;
  slug: string;
  welcome_text: string;
  logo: string | null;
  primary_color: string;
  is_active: boolean;
  require_email: boolean;
  require_name: boolean;
  default_document_type: number | null;
  max_file_size_mb: number;
  allowed_mime_types: string[];
  created_at: string;
}

export interface DocumentRequest {
  id: number;
  portal: number;
  portal_name: string;
  title: string;
  description: string;
  assignee_email: string;
  assignee_name: string;
  deadline: string | null;
  token: string;
  status: string;
  sent_at: string | null;
  reminder_sent_at: string | null;
  created_at: string;
}

export interface PortalSubmission {
  id: number;
  portal: number;
  portal_name: string;
  request: number | null;
  original_filename: string;
  submitter_email: string;
  submitter_name: string;
  status: string;
  review_notes: string;
  submitted_at: string;
  ingested_document: number | null;
}

export interface PublicPortalInfo {
  name: string;
  welcome_text: string;
  logo: string | null;
  primary_color: string;
  require_email: boolean;
  require_name: boolean;
  max_file_size_mb: number;
  allowed_mime_types: string[];
}

export interface PublicRequestInfo {
  title: string;
  description: string;
  deadline: string | null;
  portal_name: string;
}
