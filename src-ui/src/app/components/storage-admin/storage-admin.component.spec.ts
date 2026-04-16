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

describe('StorageAdminComponent', () => {
  let fixture: ComponentFixture<StorageAdminComponent>;
  let component: StorageAdminComponent;
  let httpTesting: HttpTestingController;

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
  });

  it('should clear dedupLoading on HTTP error', () => {
    fixture.detectChanges();
    const req = httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`);
    req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });

    expect(component.dedupLoading()).toBe(false);
    expect(component.dedupStats()).toBeNull();
  });

  it('should set dedupLoading to true before response', () => {
    fixture.detectChanges();
    expect(component.dedupLoading()).toBe(true);
    // Flush to keep afterEach tidy
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);
  });

  it('should re-load dedup stats when loadDedupStats() is called again', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);

    component.loadDedupStats();
    const req = httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`);
    req.flush({ ...mockDedupStats, total_blobs: 600 });

    expect(component.dedupStats()!.total_blobs).toBe(600);
  });

  // --- runIntegrityCheck ---

  it('should POST to /storage/verify-integrity/ and set integrityResult', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);

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
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);

    component.runIntegrityCheck();
    const req = httpTesting.expectOne(`${apiUrl}/storage/verify-integrity/`);
    req.flush('Error', { status: 500, statusText: 'Internal Server Error' });

    expect(component.integrityRunning()).toBe(false);
    expect(component.integrityResult()).toBeNull();
  });

  it('should clear previous integrity result when runIntegrityCheck starts', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${apiUrl}/storage/dedup-stats/`).flush(mockDedupStats);

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
});
