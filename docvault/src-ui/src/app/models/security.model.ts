export interface Signature {
  id: number;
  document: number;
  signer: number;
  signer_username: string;
  signature_data: string;
  key_id: string;
  algorithm: string;
  verified: boolean;
  verified_at: string | null;
  created_at: string;
}

export interface OTPStatus {
  enabled: boolean;
  confirmed: boolean;
}

export interface OTPSetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code_base64: string;
}

export interface OTPConfirmResponse {
  confirmed: boolean;
  backup_codes: string[];
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  user: number | null;
  username: string;
  action: string;
  model_type: string;
  object_id: number | null;
  detail: string;
  ip_address: string | null;
  user_agent: string;
}

export interface GPGKey {
  key_id: string;
  fingerprint: string;
  uids: string[];
  expires: string;
  length: string;
}

export interface ScannerDevice {
  id: string;
  vendor: string;
  model: string;
  type: string;
  label: string;
}
