/** Types for the storage admin API (`/api/v1/storage/…`). */

export type StorageBackendId = 'local' | 's3' | 'b2' | 'minio' | 'r2';

/** Blank means "use the provider preset". */
export type AddressingStyle = '' | 'auto' | 'path' | 'virtual';

export type StorageConfigSource = 'database' | 'environment';

export interface DedupStats {
  total_blobs: number;
  total_size_bytes: number;
  deduplicated_size_bytes: number;
  savings_bytes: number;
  savings_percent: number;
}

export interface IntegrityResult {
  total_checked: number;
  passed: number;
  failed: number;
  errors: Array<{ file: string; reason: string }>;
}

/**
 * The stored configuration. `secret_key` is write-only server-side and is
 * never returned — `has_secret_key` reports whether one is held.
 */
export interface StorageConfig {
  enabled: boolean;
  backend: StorageBackendId;
  bucket_name: string;
  endpoint_url: string;
  region: string;
  access_key: string;
  has_secret_key: boolean;
  prefix: string;
  addressing_style: AddressingStyle;
  disable_checksums: boolean | null;
  auto_create_bucket: boolean;
  requires_endpoint: boolean;
  updated_at: string;
  effective_backend: string;
  /** Absent on the PATCH response; derive it from `enabled` when missing. */
  source?: StorageConfigSource;
  /** Present on PATCH only when the backend changed. Documents are not migrated. */
  warning?: string;
}

/**
 * Partial update body. `secret_key` is omitted entirely to keep the stored
 * secret; sending an empty string would clear it.
 */
export interface StorageConfigUpdate {
  enabled?: boolean;
  backend?: StorageBackendId;
  bucket_name?: string;
  endpoint_url?: string;
  region?: string;
  access_key?: string;
  secret_key?: string;
  prefix?: string;
  addressing_style?: AddressingStyle;
  disable_checksums?: boolean | null;
  auto_create_bucket?: boolean;
}

/** Candidate credentials probed before they are committed. */
export interface StorageTestRequest {
  backend: StorageBackendId;
  bucket_name?: string;
  endpoint_url?: string;
  region?: string;
  access_key?: string;
  secret_key?: string;
  prefix?: string;
  addressing_style?: AddressingStyle;
  disable_checksums?: boolean | null;
}

export interface StorageTestResult {
  ok: boolean;
  provider?: string;
  bucket?: string;
  prefix?: string;
  detail?: string;
  error?: string;
}

export interface StorageBackendOption {
  id: StorageBackendId;
  label: string;
  object_storage: boolean;
  requires_endpoint: boolean;
  active: boolean;
}

export interface StorageBackendsResponse {
  backends: StorageBackendOption[];
  effective: string;
}
