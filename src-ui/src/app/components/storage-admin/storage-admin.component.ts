import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StorageService } from '../../services/storage.service';
import {
  AddressingStyle,
  DedupStats,
  IntegrityResult,
  StorageBackendId,
  StorageBackendOption,
  StorageConfig,
  StorageConfigSource,
  StorageConfigUpdate,
  StorageTestRequest,
  StorageTestResult,
} from '../../models/storage.model';
import { SubnavComponent } from '../subnav/subnav.component';

/** Backends with no default endpoint — the operator must supply one. */
const ENDPOINT_REQUIRED: readonly StorageBackendId[] = ['b2', 'minio', 'r2'];

/**
 * Shown until `/storage/backends/` answers, so the selector is never empty.
 * Labels mirror `StorageConfig.Backend.choices` server-side.
 */
const FALLBACK_BACKENDS: readonly StorageBackendOption[] = [
  { id: 'local', label: 'Local filesystem', object_storage: false, requires_endpoint: false, active: false },
  { id: 's3', label: 'Amazon S3', object_storage: true, requires_endpoint: false, active: false },
  { id: 'b2', label: 'Backblaze B2', object_storage: true, requires_endpoint: true, active: false },
  { id: 'minio', label: 'MinIO', object_storage: true, requires_endpoint: true, active: false },
  { id: 'r2', label: 'Cloudflare R2', object_storage: true, requires_endpoint: true, active: false },
];

@Component({
  selector: 'app-storage-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  templateUrl: './storage-admin.component.html',
  styleUrl: './storage-admin.component.scss',
})
export class StorageAdminComponent implements OnInit {
  dedupStats = signal<DedupStats | null>(null);
  dedupLoading = signal(false);

  integrityResult = signal<IntegrityResult | null>(null);
  integrityRunning = signal(false);

  // --- Backends ---
  backends = signal<StorageBackendOption[]>([]);
  backendsLoading = signal(false);
  effectiveBackend = signal('');

  // --- Configuration ---
  config = signal<StorageConfig | null>(null);
  configLoading = signal(false);
  configSource = signal<StorageConfigSource>('environment');
  updatedAt = signal('');
  hasSecretKey = signal(false);

  saving = signal(false);
  saveMessage = signal('');
  saveError = signal('');
  /** Set from the PATCH response `warning`: the backend moved, documents did not. */
  saveWarning = signal('');

  testing = signal(false);
  testResult = signal<StorageTestResult | null>(null);

  // Form state. Plain fields bound with ngModel, as in the other admin screens.
  formEnabled = false;
  formBackend: StorageBackendId = 'local';
  formBucketName = '';
  formEndpointUrl = '';
  formRegion = '';
  formAccessKey = '';
  /** Blank means "keep whatever is stored"; it is never sent empty. */
  formSecretKey = '';
  formPrefix = '';
  formAddressingStyle: AddressingStyle = '';
  /** Tri-state as a select value: '' = provider default. */
  formDisableChecksums: '' | 'true' | 'false' = '';
  formAutoCreateBucket = false;

  constructor(private storage: StorageService) {}

  ngOnInit(): void {
    this.loadDedupStats();
    this.loadConfig();
    this.loadBackends();
  }

  // --- Deduplication ---

  loadDedupStats(): void {
    this.dedupLoading.set(true);
    this.storage.getDedupStats().subscribe({
      next: (stats) => {
        this.dedupStats.set(stats);
        this.dedupLoading.set(false);
      },
      error: () => this.dedupLoading.set(false),
    });
  }

  runIntegrityCheck(): void {
    this.integrityRunning.set(true);
    this.integrityResult.set(null);
    this.storage.verifyIntegrity().subscribe({
      next: (result) => {
        this.integrityResult.set(result);
        this.integrityRunning.set(false);
      },
      error: () => this.integrityRunning.set(false),
    });
  }

  // --- Backends ---

  loadBackends(): void {
    this.backendsLoading.set(true);
    this.storage.getBackends().subscribe({
      next: (response) => {
        this.backends.set(response.backends);
        this.effectiveBackend.set(response.effective);
        this.backendsLoading.set(false);
      },
      error: () => this.backendsLoading.set(false),
    });
  }

  /** API list once loaded, otherwise the static fallback. */
  get backendOptions(): readonly StorageBackendOption[] {
    return this.backends().length ? this.backends() : FALLBACK_BACKENDS;
  }

  // --- Configuration ---

  loadConfig(): void {
    this.configLoading.set(true);
    this.storage.getConfig().subscribe({
      next: (config) => {
        this.applyConfig(config);
        this.configLoading.set(false);
      },
      error: () => this.configLoading.set(false),
    });
  }

  /** Copy a server response into the form. Never fills the secret key. */
  private applyConfig(config: StorageConfig): void {
    this.config.set(config);
    this.formEnabled = config.enabled;
    this.formBackend = config.backend;
    this.formBucketName = config.bucket_name ?? '';
    this.formEndpointUrl = config.endpoint_url ?? '';
    this.formRegion = config.region ?? '';
    this.formAccessKey = config.access_key ?? '';
    this.formPrefix = config.prefix ?? '';
    this.formAddressingStyle = config.addressing_style ?? '';
    this.formDisableChecksums =
      config.disable_checksums === null || config.disable_checksums === undefined
        ? ''
        : config.disable_checksums
          ? 'true'
          : 'false';
    this.formAutoCreateBucket = config.auto_create_bucket;
    this.hasSecretKey.set(config.has_secret_key);
    this.effectiveBackend.set(config.effective_backend ?? this.effectiveBackend());
    // PATCH responses carry no `source`; it follows directly from `enabled`.
    this.configSource.set(config.source ?? (config.enabled ? 'database' : 'environment'));
    this.updatedAt.set(config.updated_at ?? '');
  }

  toggleEnabled(): void {
    this.formEnabled = !this.formEnabled;
  }

  toggleAutoCreateBucket(): void {
    this.formAutoCreateBucket = !this.formAutoCreateBucket;
  }

  /** Local filesystem storage has no bucket, endpoint or credentials. */
  get isObjectStorage(): boolean {
    return this.formBackend !== 'local';
  }

  /** B2, MinIO and R2 have no default endpoint, so one must be supplied. */
  get endpointRequired(): boolean {
    const known = this.backends().find((backend) => backend.id === this.formBackend);
    return known ? known.requires_endpoint : ENDPOINT_REQUIRED.includes(this.formBackend);
  }

  /** Blocks Save while a required endpoint is missing. */
  get endpointMissing(): boolean {
    return this.isObjectStorage && this.endpointRequired && !this.formEndpointUrl.trim();
  }

  private disableChecksumsValue(): boolean | null {
    if (this.formDisableChecksums === 'true') return true;
    if (this.formDisableChecksums === 'false') return false;
    return null;
  }

  /**
   * The PATCH body. `secret_key` is included only when the operator typed a new
   * one — sending an empty string would clear the stored secret.
   */
  private configPayload(): StorageConfigUpdate {
    const payload: StorageConfigUpdate = {
      enabled: this.formEnabled,
      backend: this.formBackend,
      bucket_name: this.formBucketName.trim(),
      endpoint_url: this.formEndpointUrl.trim(),
      region: this.formRegion.trim(),
      access_key: this.formAccessKey.trim(),
      prefix: this.formPrefix.trim(),
      addressing_style: this.formAddressingStyle,
      disable_checksums: this.disableChecksumsValue(),
      auto_create_bucket: this.formAutoCreateBucket,
    };
    if (this.formSecretKey) {
      payload.secret_key = this.formSecretKey;
    }
    return payload;
  }

  /** Candidate values for the probe. Same secret-key rule as the PATCH body. */
  private testPayload(): StorageTestRequest {
    const payload: StorageTestRequest = {
      backend: this.formBackend,
      bucket_name: this.formBucketName.trim(),
      endpoint_url: this.formEndpointUrl.trim(),
      region: this.formRegion.trim(),
      access_key: this.formAccessKey.trim(),
      prefix: this.formPrefix.trim(),
      addressing_style: this.formAddressingStyle,
    };
    const checksums = this.disableChecksumsValue();
    if (checksums !== null) {
      payload.disable_checksums = checksums;
    }
    if (this.formSecretKey) {
      payload.secret_key = this.formSecretKey;
    }
    return payload;
  }

  testConnection(): void {
    this.testing.set(true);
    this.testResult.set(null);
    this.storage.testConnection(this.testPayload()).subscribe({
      next: (result) => {
        this.testResult.set(result);
        this.testing.set(false);
      },
      error: (err: unknown) => {
        // A failed probe answers 400 with the same {ok:false, error} body.
        this.testResult.set({ ok: false, error: this.errorText(err, 'Connection test failed.') });
        this.testing.set(false);
      },
    });
  }

  saveConfig(): void {
    this.saving.set(true);
    this.saveError.set('');
    this.saveMessage.set('');
    this.saveWarning.set('');

    this.storage.updateConfig(this.configPayload()).subscribe({
      next: (config) => {
        // applyConfig() refreshes has_secret_key from the response; clearing the
        // typed value keeps it out of the DOM and makes the next save omit it.
        this.applyConfig(config);
        this.formSecretKey = '';
        this.saveMessage.set('Storage configuration saved.');
        this.saveWarning.set(config.warning ?? '');
        this.saving.set(false);
        // The active backend may have moved.
        this.loadBackends();
      },
      error: (err: unknown) => {
        this.saveError.set(this.errorText(err, 'Failed to save storage configuration.'));
        this.saving.set(false);
      },
    });
  }

  dismissTestResult(): void {
    this.testResult.set(null);
  }

  dismissSaveMessage(): void {
    this.saveMessage.set('');
  }

  dismissSaveError(): void {
    this.saveError.set('');
  }

  dismissSaveWarning(): void {
    this.saveWarning.set('');
  }

  /** Pull the server's message out of an HttpErrorResponse, verbatim. */
  private errorText(err: unknown, fallback: string): string {
    const body = (err as { error?: unknown } | null)?.error;
    if (typeof body === 'string' && body.trim()) return body;
    if (body && typeof body === 'object') {
      const record = body as Record<string, unknown>;
      for (const key of ['error', 'detail']) {
        if (typeof record[key] === 'string' && record[key]) return record[key] as string;
      }
      // DRF field errors: {"endpoint_url": ["Required for r2; …"]}
      const parts: string[] = [];
      for (const [field, value] of Object.entries(record)) {
        if (Array.isArray(value)) parts.push(`${field}: ${value.join(' ')}`);
        else if (typeof value === 'string') parts.push(`${field}: ${value}`);
      }
      if (parts.length) return parts.join(' · ');
    }
    return fallback;
  }

  formatBytes(bytes: number): string {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
  }
}
