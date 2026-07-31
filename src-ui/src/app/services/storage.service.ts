import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  DedupStats,
  IntegrityResult,
  StorageBackendsResponse,
  StorageConfig,
  StorageConfigUpdate,
  StorageTestRequest,
  StorageTestResult,
} from '../models/storage.model';

/** Storage administration endpoints. All of them are admin-only server-side. */
@Injectable({ providedIn: 'root' })
export class StorageService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getDedupStats(): Observable<DedupStats> {
    return this.http.get<DedupStats>(`${this.apiUrl}/storage/dedup-stats/`);
  }

  verifyIntegrity(): Observable<IntegrityResult> {
    return this.http.post<IntegrityResult>(`${this.apiUrl}/storage/verify-integrity/`, {});
  }

  getConfig(): Observable<StorageConfig> {
    return this.http.get<StorageConfig>(`${this.apiUrl}/storage/config/`);
  }

  /**
   * Partial update. Leave `secret_key` off the body to keep the stored secret —
   * an empty string would clear it.
   */
  updateConfig(data: StorageConfigUpdate): Observable<StorageConfig> {
    return this.http.patch<StorageConfig>(`${this.apiUrl}/storage/config/`, data);
  }

  /** An empty body tests what is stored; a populated one tests candidate values. */
  testConnection(data: StorageTestRequest | Record<string, never> = {}): Observable<StorageTestResult> {
    return this.http.post<StorageTestResult>(`${this.apiUrl}/storage/config/test/`, data);
  }

  getBackends(): Observable<StorageBackendsResponse> {
    return this.http.get<StorageBackendsResponse>(`${this.apiUrl}/storage/backends/`);
  }
}
