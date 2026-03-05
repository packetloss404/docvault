export interface Signer {
  id: number;
  name: string;
  email: string;
  role: string;
  order: number;
  token?: string;
  status: 'pending' | 'viewed' | 'signed' | 'declined';
  signed_at: string | null;
  verification_method: 'email' | 'sms' | 'none';
  viewed_pages: number[];
}

export interface SignatureField {
  id: number;
  signer: number;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  field_type: 'signature' | 'initials' | 'date' | 'text' | 'checkbox';
  required: boolean;
  order: number;
  value: string;
  signed_at: string | null;
}

export interface SignatureRequest {
  id: number;
  document: number;
  title: string;
  message: string;
  status:
    | 'draft'
    | 'sent'
    | 'in_progress'
    | 'completed'
    | 'cancelled'
    | 'expired';
  signing_order: 'sequential' | 'parallel';
  expiration: string | null;
  completed_at: string | null;
  signers: Signer[];
  fields: SignatureField[];
  created_at: string;
  updated_at: string;
}

export interface SignatureAuditEvent {
  id: number;
  signer: number | null;
  event_type: string;
  detail: Record<string, any>;
  ip_address: string | null;
  timestamp: string;
}

export interface PublicSigningInfo {
  request_title: string;
  document_title: string;
  signer_name: string;
  signer_role: string;
  fields: SignatureField[];
  page_count: number;
  viewed_pages: number[];
  status: string;
}
