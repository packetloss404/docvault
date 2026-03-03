export interface Source {
  id: number;
  label: string;
  enabled: boolean;
  source_type: 'watch_folder' | 'email' | 'staging' | 's3';
  document_type: number | null;
  tags: number[];
  owner: number | null;
  created_at: string;
  updated_at: string;
}

export interface WatchFolderSource {
  id: number;
  source: number;
  path: string;
  polling_interval: number;
  consumed_action: 'delete' | 'move' | 'nothing';
  consumed_directory: string;
}

export interface MailAccount {
  id: number;
  name: string;
  enabled: boolean;
  imap_server: string;
  port: number;
  security: 'none' | 'ssl' | 'starttls';
  account_type: 'imap' | 'gmail_oauth' | 'outlook_oauth';
  username: string;
  password: string;
}

export interface MailRule {
  id: number;
  name: string;
  enabled: boolean;
  account: number;
  folder: string;
  filter_from: string;
  filter_subject: string;
  filter_body: string;
  filter_attachment_filename: string;
  maximum_age: number;
  action: 'download_attachment' | 'process_email';
  document_type: number | null;
  tags: number[];
  owner: number | null;
  processed_action: 'mark_read' | 'move_to_folder' | 'delete' | 'flag';
  processed_folder: string;
  order: number;
}

export interface WorkflowRule {
  id: number;
  name: string;
  enabled: boolean;
  order: number;
  trigger_ids: number[];
  action_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowTrigger {
  id: number;
  type: 'consumption' | 'document_added' | 'document_updated' | 'scheduled';
  filter_filename: string;
  filter_path: string;
  filter_has_tags: number[];
  filter_has_correspondent: number | null;
  filter_has_document_type: number | null;
  filter_custom_field_query: Record<string, unknown>;
  match_pattern: string;
  matching_algorithm: number;
  schedule_interval_minutes: number | null;
  enabled: boolean;
}

export interface WorkflowRuleAction {
  id: number;
  type: string;
  configuration: Record<string, unknown>;
  order: number;
  enabled: boolean;
}
