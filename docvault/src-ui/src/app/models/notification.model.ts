export interface Notification {
  id: number;
  event_type: string;
  title: string;
  body: string;
  document: number | null;
  read: boolean;
  created_at: string;
}

export interface NotificationPreference {
  id: number;
  event_type: string;
  channel: 'in_app' | 'email' | 'webhook';
  enabled: boolean;
  webhook_url: string;
}

export interface QuotaUsage {
  document_count: number;
  storage_bytes: number;
  max_documents: number | null;
  max_storage_bytes: number | null;
  documents_remaining: number | null;
  storage_remaining: number | null;
}
