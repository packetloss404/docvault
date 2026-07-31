import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi, describe, beforeEach, afterEach, it, expect } from 'vitest';

import { StorageAdminComponent } from './storage-admin.component';
import { environment } from '../../../environments/environment';

const apiUrl = environment.apiUrl;

const mockDedupStats = {
  total_blobs: 500,
  total_size_bytes: 10_000_000,
  deduplicated_size_bytes: 7_000_000,
  savings_bytes: 3_000_000,
  savings_percent: 30,
};

const mockIntegrityResult = {
  total_checked: 100,
  passed: 98,
  failed: 2,
  errors: [
    { file: 'doc1.pdf', reason: 'checksum mismatch' },
    { file: 'doc2.pdf', reason: 'missing blob' },
  ],
};

const mockConfig = {
  enabled: true,
  backend: 's3' as const,
  bucket_name: 'docvault',
  endpoint_url: '',
  region: 'us-east-1',
  access_key: 'AKIAEXAMPLE',
  has_secret_key: true,
  prefix: 'documents',
  addressing_style: '' as const,
  disable_checksums: null,
  auto_create_bucket: false,
  requires_endpoint: false,
  updated_at: '2026-07-01T10:00:00Z',
  effective_backend: 's3',
  source: 'database' as const,
};

const mockBackends = {
  backends: [
    {
      id: 'local' as const,
      label: 'Local filesystem',
      object_storage: false,
      requires_endpoint: false,
      active: false,
    },
    {
      id: 's3' as const,
      label: 'Amazon S3',
      object_storage: true,
      requires_endpoint: false,
      active: true,
    },
    {
      id: 'b2' as const,
      label: 'Backblaze B2',
      object_storage: true,
      requires_endpoint: true,
      active: false,
    },
    {
      id: 'minio' as const,
      label: 'MinIO',
      object_storage: true,
      requires_endpoint: true,
      active: false,
    },
    {
      id: 'r2' as const,
      label: 'Cloudflare R2',
      object_storage: true,
      requires_endpoint: true,
      active: false,
    },
  ],
  effective: 's3',
};

describe('StorageAdminComponent', () => {
  let fixture: ComponentFixture<StorageAdminComponent>;
  let component: StorageAdminComponent;
  let httpTesting: HttpTestingController;

  /**
   * ngOnInit also loads the configuration and the backend list. Existing tests
   * assert on the dedup request themselves; this drains the other two so
   * `httpTesting.verify()` stays clean.
   */
  const flushSideLoads = (): void => {
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);
  };

  /** Full init: dedup stats + configuration + backends. */
  const initAll = (): void => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    flushSideLoads();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StorageAdminComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StorageAdminComponent);
    component = fixture.componentInstance;
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should create', () => {
    // Flush the auto-triggered loadDedupStats GET
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    flushSideLoads();
    expect(component).toBeTruthy();
  });

  // --- loadDedupStats ---

  it('should call GET /storage/dedup-stats/ on init and set dedupStats', () => {
    fixture.detectChanges();

    const req = httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`);
    expect(req.request.method).toBe('GET');

    expect(component.dedupLoading()).toBe(true);
    req.flush(mockDedupStats);

    expect(component.dedupStats()).toEqual(mockDedupStats);
    expect(component.dedupLoading()).toBe(false);
    flushSideLoads();
  });

  it('should clear dedupLoading on HTTP error', () => {
    fixture.detectChanges();
    const req = httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`);
    req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });

    expect(component.dedupLoading()).toBe(false);
    expect(component.dedupStats()).toBeNull();
    flushSideLoads();
  });

  it('should set dedupLoading to true before response', () => {
    fixture.detectChanges();
    expect(component.dedupLoading()).toBe(true);
    // Flush to keep afterEach tidy
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    flushSideLoads();
  });

  it('should re-load dedup stats when loadDedupStats() is called again', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    flushSideLoads();

    component.loadDedupStats();
    const req = httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`);
    req.flush({ ...mockDedupStats, total_blobs: 600 });

    expect(component.dedupStats()!.total_blobs).toBe(600);
  });

  // --- runIntegrityCheck ---

  it('should POST to /storage/verify-integrity/ and set integrityResult', () => {
    initAll();

    component.runIntegrityCheck();

    expect(component.integrityRunning()).toBe(true);
    expect(component.integrityResult()).toBeNull();

    const req = httpTesting.expectOne(`${apiUrl}/storage/verify-integrity/`);
    expect(req.request.method).toBe('POST');
    req.flush(mockIntegrityResult);

    expect(component.integrityResult()).toEqual(mockIntegrityResult);
    expect(component.integrityRunning()).toBe(false);
  });

  it('should clear integrityRunning on integrity check HTTP error', () => {
    initAll();

    component.runIntegrityCheck();
    const req = httpTesting.expectOne(`${apiUrl}/storage/verify-integrity/`);
    req.flush('Error', { status: 500, statusText: 'Internal Server Error' });

    expect(component.integrityRunning()).toBe(false);
    expect(component.integrityResult()).toBeNull();
  });

  it('should clear previous integrity result when runIntegrityCheck starts', () => {
    initAll();

    // Set a previous result
    component.integrityResult.set(mockIntegrityResult);

    component.runIntegrityCheck();
    expect(component.integrityResult()).toBeNull();

    // Flush to keep afterEach clean
    httpTesting.expectOne(`${apiUrl}/storage/verify-integrity/`).flush(mockIntegrityResult);
  });

  // --- formatBytes ---

  it('formatBytes should return "0 B" for 0', () => {
    expect(component.formatBytes(0)).toBe('0 B');
  });

  it('formatBytes should format bytes under 1 KB as B', () => {
    expect(component.formatBytes(512)).toBe('512.0 B');
  });

  it('formatBytes should format kilobytes correctly', () => {
    expect(component.formatBytes(1024)).toBe('1.0 KB');
  });

  it('formatBytes should format megabytes correctly', () => {
    expect(component.formatBytes(1024 * 1024)).toBe('1.0 MB');
  });

  it('formatBytes should format gigabytes correctly', () => {
    expect(component.formatBytes(1024 * 1024 * 1024)).toBe('1.0 GB');
  });

  it('formatBytes should format terabytes correctly', () => {
    expect(component.formatBytes(1024 ** 4)).toBe('1.0 TB');
  });

  it('formatBytes should handle non-round values', () => {
    // 1.5 MB
    expect(component.formatBytes(1024 * 1024 * 1.5)).toBe('1.5 MB');
  });

  it('formatBytes should handle large savings bytes from mock', () => {
    // 3_000_000 bytes ≈ 2.9 MB
    const result = component.formatBytes(3_000_000);
    expect(result).toMatch(/MB$/);
  });

  // --- backends ---

  it('should GET /storage/backends/ on init and record the effective backend', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush(mockConfig);

    const req = httpTesting.expectOne(`${apiUrl}/storage/backends/`);
    expect(req.request.method).toBe('GET');
    req.flush(mockBackends);

    expect(component.backends().length).toBe(5);
    expect(component.effectiveBackend()).toBe('s3');
    expect(component.backends().find((b) => b.active)!.id).toBe('s3');
  });

  it('should fall back to the static backend list before the API answers', () => {
    expect(component.backends().length).toBe(0);
    expect(component.backendOptions.map((b) => b.id)).toEqual([
      'local',
      's3',
      'b2',
      'minio',
      'r2',
    ]);
    // No detectChanges: nothing to flush.
  });

  it('should prefer the API backend list once loaded', () => {
    initAll();
    expect(component.backendOptions).toBe(component.backends());
  });

  it('should clear backendsLoading on backends HTTP error', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush(mockConfig);
    httpTesting
      .expectOne(`${apiUrl}/storage/backends/`)
      .flush('boom', { status: 500, statusText: 'Server Error' });

    expect(component.backendsLoading()).toBe(false);
    expect(component.backends()).toEqual([]);
  });

  // --- loadConfig ---

  it('should GET /storage/config/ on init and populate the form', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/`);
    expect(req.request.method).toBe('GET');
    req.flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);

    expect(component.formEnabled).toBe(true);
    expect(component.formBackend).toBe('s3');
    expect(component.formBucketName).toBe('docvault');
    expect(component.formRegion).toBe('us-east-1');
    expect(component.formPrefix).toBe('documents');
    expect(component.configSource()).toBe('database');
    expect(component.effectiveBackend()).toBe('s3');
    expect(component.configLoading()).toBe(false);
  });

  it('should never populate the secret key field from the API', () => {
    initAll();
    expect(component.formSecretKey).toBe('');
    expect(component.hasSecretKey()).toBe(true);
  });

  it('should map a null disable_checksums onto the blank tri-state', () => {
    initAll();
    expect(component.formDisableChecksums).toBe('');
  });

  it('should map disable_checksums true/false onto the tri-state', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    httpTesting
      .expectOne(`${apiUrl}/storage/config/`)
      .flush({ ...mockConfig, disable_checksums: true });
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);
    expect(component.formDisableChecksums).toBe('true');

    component.loadConfig();
    httpTesting
      .expectOne(`${apiUrl}/storage/config/`)
      .flush({ ...mockConfig, disable_checksums: false });
    expect(component.formDisableChecksums).toBe('false');
  });

  it('should clear configLoading on config HTTP error', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
    httpTesting
      .expectOne(`${apiUrl}/storage/config/`)
      .flush('nope', { status: 500, statusText: 'Server Error' });
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);

    expect(component.configLoading()).toBe(false);
    expect(component.config()).toBeNull();
  });

  // --- field visibility per backend ---

  it('should hide the object-storage fields for the local backend', () => {
    initAll();
    component.formBackend = 'local';
    expect(component.isObjectStorage).toBe(false);
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).innerHTML;
    expect(html).not.toContain('sa-bucket');
    expect(html).not.toContain('sa-secret-key');
  });

  it('should show the object-storage fields for an object backend', () => {
    initAll();
    component.formBackend = 's3';
    expect(component.isObjectStorage).toBe(true);
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).innerHTML;
    expect(html).toContain('sa-bucket');
    expect(html).toContain('sa-endpoint');
    expect(html).toContain('sa-secret-key');
    expect(html).toContain('sa-checksums');
  });

  // --- endpoint-required rule ---

  it('should not require an endpoint for s3 or local', () => {
    initAll();
    component.formBackend = 's3';
    expect(component.endpointRequired).toBe(false);
    component.formBackend = 'local';
    expect(component.endpointRequired).toBe(false);
  });

  it('should require an endpoint for b2, minio and r2', () => {
    initAll();
    for (const backend of ['b2', 'minio', 'r2'] as const) {
      component.formBackend = backend;
      expect(component.endpointRequired).toBe(true);
    }
  });

  it('should require an endpoint from the static table when backends have not loaded', () => {
    expect(component.backends().length).toBe(0);
    component.formBackend = 'r2';
    expect(component.endpointRequired).toBe(true);
    component.formBackend = 's3';
    expect(component.endpointRequired).toBe(false);
  });

  it('should flag a missing endpoint only for backends that need one', () => {
    initAll();
    component.formBackend = 'minio';
    component.formEndpointUrl = '   ';
    expect(component.endpointMissing).toBe(true);

    component.formEndpointUrl = 'https://minio.example.com';
    expect(component.endpointMissing).toBe(false);

    component.formBackend = 's3';
    component.formEndpointUrl = '';
    expect(component.endpointMissing).toBe(false);
  });

  it('should disable Save while a required endpoint is missing', () => {
    initAll();
    component.formBackend = 'b2';
    component.formEndpointUrl = '';
    fixture.detectChanges();

    const save = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>(
      '.dv-btn--primary',
    )!;
    expect(save.disabled).toBe(true);
  });

  // --- secret key omit-vs-send ---

  it('should omit secret_key from the PATCH when nothing was typed', () => {
    initAll();
    component.formSecretKey = '';
    component.saveConfig();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/`);
    expect(req.request.method).toBe('PATCH');
    expect('secret_key' in (req.request.body as Record<string, unknown>)).toBe(false);
    req.flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);
  });

  it('should send secret_key on the PATCH when a new one was typed', () => {
    initAll();
    component.formSecretKey = 'brand-new-secret';
    component.saveConfig();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/`);
    expect((req.request.body as Record<string, unknown>)['secret_key']).toBe('brand-new-secret');
    req.flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);

    // Consumed: it is not resent on the next save.
    expect(component.formSecretKey).toBe('');
  });

  it('should omit secret_key from the connection test when nothing was typed', () => {
    initAll();
    component.formSecretKey = '';
    component.testConnection();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/test/`);
    expect(req.request.method).toBe('POST');
    expect('secret_key' in (req.request.body as Record<string, unknown>)).toBe(false);
    req.flush({ ok: true, provider: 's3', bucket: 'docvault', prefix: 'documents' });
  });

  it('should send secret_key on the connection test when one was typed', () => {
    initAll();
    component.formSecretKey = 'probe-secret';
    component.testConnection();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/test/`);
    expect((req.request.body as Record<string, unknown>)['secret_key']).toBe('probe-secret');
    req.flush({ ok: true, provider: 's3' });

    // The test does not consume the typed secret — Save still needs it.
    expect(component.formSecretKey).toBe('probe-secret');
  });

  // --- PATCH body ---

  it('should send the tri-state disable_checksums as null when blank', () => {
    initAll();
    component.formDisableChecksums = '';
    component.saveConfig();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/`);
    expect((req.request.body as Record<string, unknown>)['disable_checksums']).toBeNull();
    req.flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);
  });

  it('should send the tri-state disable_checksums as a boolean when set', () => {
    initAll();
    component.formDisableChecksums = 'true';
    component.saveConfig();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/`);
    expect((req.request.body as Record<string, unknown>)['disable_checksums']).toBe(true);
    req.flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);
  });

  it('should omit disable_checksums from the test body when blank', () => {
    initAll();
    component.formDisableChecksums = '';
    component.testConnection();

    const req = httpTesting.expectOne(`${apiUrl}/storage/config/test/`);
    expect('disable_checksums' in (req.request.body as Record<string, unknown>)).toBe(false);
    req.flush({ ok: true, provider: 's3' });
  });

  // --- save ---

  it('should surface the warning from a save that changed the backend', () => {
    initAll();
    component.formBackend = 'r2';
    component.formEndpointUrl = 'https://r2.example.com';
    component.saveConfig();

    const warning =
      "Backend changed from 's3' to 'r2'. Existing documents are not migrated and " +
      'will not resolve until they are moved.';
    httpTesting
      .expectOne(`${apiUrl}/storage/config/`)
      .flush({ ...mockConfig, backend: 'r2', effective_backend: 'r2', warning });
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);

    expect(component.saveWarning()).toBe(warning);
    expect(component.saveMessage()).toBe('Storage configuration saved.');
    expect(component.saving()).toBe(false);

    fixture.detectChanges();
    const callout = (fixture.nativeElement as HTMLElement).querySelector('.dv-callout--warn[role="alert"]');
    expect(callout?.textContent).toContain('not migrated');
  });

  it('should leave the warning empty when the backend did not change', () => {
    initAll();
    component.saveConfig();
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush(mockConfig);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);

    expect(component.saveWarning()).toBe('');
    expect(component.saveMessage()).toBe('Storage configuration saved.');
  });

  it('should surface a DRF field error when the save is rejected', () => {
    initAll();
    component.saveConfig();
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush(
      { endpoint_url: ['Required for r2; it has no default endpoint.'] },
      { status: 400, statusText: 'Bad Request' },
    );

    expect(component.saving()).toBe(false);
    expect(component.saveError()).toContain('endpoint_url');
    expect(component.saveError()).toContain('no default endpoint');
    // No backends reload on failure.
  });

  it('should refresh the backend list after a successful save', () => {
    initAll();
    component.saveConfig();
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush({ ...mockConfig, backend: 'b2' });

    const req = httpTesting.expectOne(`${apiUrl}/storage/backends/`);
    expect(req.request.method).toBe('GET');
    req.flush({
      ...mockBackends,
      effective: 'b2',
      backends: mockBackends.backends.map((b) => ({ ...b, active: b.id === 'b2' })),
    });

    expect(component.effectiveBackend()).toBe('b2');
  });

  it('should derive the source from enabled when the PATCH response omits it', () => {
    initAll();
    expect(component.configSource()).toBe('database');

    component.saveConfig();
    const withoutSource: Record<string, unknown> = { ...mockConfig, enabled: false };
    delete withoutSource['source'];
    httpTesting.expectOne(`${apiUrl}/storage/config/`).flush(withoutSource);
    httpTesting.expectOne(`${apiUrl}/storage/backends/`).flush(mockBackends);

    expect(component.configSource()).toBe('environment');
  });

  // --- test connection ---

  it('should record a successful connection test', () => {
    initAll();
    component.testConnection();
    expect(component.testing()).toBe(true);

    httpTesting
      .expectOne(`${apiUrl}/storage/config/test/`)
      .flush({ ok: true, provider: 's3', bucket: 'docvault', prefix: 'documents' });

    expect(component.testing()).toBe(false);
    expect(component.testResult()).toEqual({
      ok: true,
      provider: 's3',
      bucket: 'docvault',
      prefix: 'documents',
    });

    fixture.detectChanges();
    const banner = (fixture.nativeElement as HTMLElement).querySelector('.dv-banner--ok');
    expect(banner?.textContent).toContain('Connection ok');
  });

  it('should render the error verbatim when the test answers 400', () => {
    initAll();
    component.testConnection();

    httpTesting
      .expectOne(`${apiUrl}/storage/config/test/`)
      .flush(
        { ok: false, error: 'An error occurred (403) when calling HeadBucket: Forbidden' },
        { status: 400, statusText: 'Bad Request' },
      );

    expect(component.testing()).toBe(false);
    expect(component.testResult()!.ok).toBe(false);
    expect(component.testResult()!.error).toBe(
      'An error occurred (403) when calling HeadBucket: Forbidden',
    );

    fixture.detectChanges();
    const banner = (fixture.nativeElement as HTMLElement).querySelector('.dv-banner--error');
    expect(banner?.textContent).toContain('HeadBucket');
  });

  it('should record an ok:false body returned with HTTP 200', () => {
    initAll();
    component.testConnection();
    httpTesting
      .expectOne(`${apiUrl}/storage/config/test/`)
      .flush({ ok: false, error: 'Invalid endpoint URL' });

    expect(component.testResult()!.ok).toBe(false);
    expect(component.testResult()!.error).toBe('Invalid endpoint URL');
  });

  it('should fall back to a generic message when the test error carries no body', () => {
    initAll();
    component.testConnection();
    httpTesting
      .expectOne(`${apiUrl}/storage/config/test/`)
      .flush(null, { status: 500, statusText: 'Server Error' });

    expect(component.testResult()!.ok).toBe(false);
    expect(component.testResult()!.error).toBe('Connection test failed.');
  });

  it('should clear a previous test result when a new test starts', () => {
    initAll();
    component.testResult.set({ ok: true, provider: 's3' });
    component.testConnection();
    expect(component.testResult()).toBeNull();

    httpTesting.expectOne(`${apiUrl}/storage/config/test/`).flush({ ok: true, provider: 's3' });
  });

  it('should dismiss banners and callouts', () => {
    initAll();
    component.testResult.set({ ok: true });
    component.dismissTestResult();
    expect(component.testResult()).toBeNull();

    component.saveMessage.set('x');
    component.dismissSaveMessage();
    expect(component.saveMessage()).toBe('');

    component.saveError.set('x');
    component.dismissSaveError();
    expect(component.saveError()).toBe('');

    component.saveWarning.set('x');
    component.dismissSaveWarning();
    expect(component.saveWarning()).toBe('');
  });

  // --- toggles ---

  it('should toggle the enabled switch', () => {
    initAll();
    expect(component.formEnabled).toBe(true);
    component.toggleEnabled();
    expect(component.formEnabled).toBe(false);
    component.toggleEnabled();
    expect(component.formEnabled).toBe(true);
  });

  it('should toggle auto-create bucket', () => {
    initAll();
    expect(component.formAutoCreateBucket).toBe(false);
    component.toggleAutoCreateBucket();
    expect(component.formAutoCreateBucket).toBe(true);
  });

  // --- backends card rendering ---

  it('should mark the active backend with an accent chip', () => {
    initAll();
    fixture.detectChanges();
    const chips = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('.dv-chip--accent'),
    ).map((el) => el.textContent!.trim());
    expect(chips).toContain('active');
  });

  it('should label object-storage backends distinctly from local', () => {
    initAll();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent!;
    expect(text).toContain('object storage');
    expect(text).toContain('Local filesystem');
    expect(text).toContain('Cloudflare R2');
  });
});
