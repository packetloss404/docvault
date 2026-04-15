import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  AuditLogEntry,
  GPGKey,
  Group,
  OTPConfirmResponse,
  OTPSetupResponse,
  OTPStatus,
  Permission,
  Role,
  ScannerDevice,
  Signature,
  User,
} from '../models/security.model';

export interface AuditLogQueryParams {
  page?: number;
  page_size?: number;
  user?: number;
  action?: string;
  model_type?: string;
  from_date?: string;
  to_date?: string;
}

@Injectable({ providedIn: 'root' })
export class SecurityService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- OTP ---

  getOTPStatus(): Observable<OTPStatus> {
    return this.http.get<OTPStatus>(`${this.apiUrl}/auth/otp/status/`);
  }

  setupOTP(): Observable<OTPSetupResponse> {
    return this.http.post<OTPSetupResponse>(`${this.apiUrl}/auth/otp/setup/`, {});
  }

  confirmOTP(code: string): Observable<OTPConfirmResponse> {
    return this.http.post<OTPConfirmResponse>(`${this.apiUrl}/auth/otp/confirm/`, { code });
  }

  disableOTP(password: string): Observable<{ disabled: boolean }> {
    return this.http.post<{ disabled: boolean }>(`${this.apiUrl}/auth/otp/disable/`, { password });
  }

  verifyOTP(code: string): Observable<{ verified: boolean; token: string }> {
    return this.http.post<{ verified: boolean; token: string }>(
      `${this.apiUrl}/auth/otp/verify/`,
      { code },
    );
  }

  // --- Signatures ---

  signDocument(documentId: number, keyId?: string): Observable<Signature> {
    const body: Record<string, string> = {};
    if (keyId) {
      body['key_id'] = keyId;
    }
    return this.http.post<Signature>(
      `${this.apiUrl}/documents/${documentId}/sign/`,
      body,
    );
  }

  getDocumentSignatures(documentId: number): Observable<Signature[]> {
    return this.http.get<Signature[]>(
      `${this.apiUrl}/documents/${documentId}/signatures/`,
    );
  }

  verifyDocumentSignatures(documentId: number): Observable<{ results: Signature[] }> {
    return this.http.post<{ results: Signature[] }>(
      `${this.apiUrl}/documents/${documentId}/verify-signatures/`,
      {},
    );
  }

  // --- GPG Keys ---

  getGPGKeys(): Observable<GPGKey[]> {
    return this.http.get<GPGKey[]>(`${this.apiUrl}/security/gpg-keys/`);
  }

  importGPGKey(keyData: string): Observable<GPGKey> {
    return this.http.post<GPGKey>(`${this.apiUrl}/security/gpg-keys/import/`, {
      key_data: keyData,
    });
  }

  deleteGPGKey(keyId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/security/gpg-keys/${keyId}/`);
  }

  // --- Audit Log ---

  getAuditLog(
    params: AuditLogQueryParams = {},
  ): Observable<PaginatedResponse<AuditLogEntry>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<PaginatedResponse<AuditLogEntry>>(
      `${this.apiUrl}/security/audit-log/`,
      { params: httpParams },
    );
  }

  exportAuditLog(
    format: 'csv' | 'json',
    params: AuditLogQueryParams = {},
  ): Observable<Blob> {
    let httpParams = new HttpParams().set('format', format);
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get(`${this.apiUrl}/security/audit-log/export/`, {
      params: httpParams,
      responseType: 'blob',
    });
  }

  // --- Users ---

  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.apiUrl}/security/users/`);
  }

  getUser(id: number): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/security/users/${id}/`);
  }

  createUser(data: Partial<User> & { password?: string }): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/security/users/`, data);
  }

  updateUser(id: number, data: Partial<User> & { password?: string }): Observable<User> {
    return this.http.patch<User>(`${this.apiUrl}/security/users/${id}/`, data);
  }

  deleteUser(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/security/users/${id}/`);
  }

  // --- Groups ---

  getGroups(): Observable<Group[]> {
    return this.http.get<Group[]>(`${this.apiUrl}/security/groups/`);
  }

  createGroup(data: Partial<Group>): Observable<Group> {
    return this.http.post<Group>(`${this.apiUrl}/security/groups/`, data);
  }

  updateGroup(id: number, data: Partial<Group>): Observable<Group> {
    return this.http.patch<Group>(`${this.apiUrl}/security/groups/${id}/`, data);
  }

  deleteGroup(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/security/groups/${id}/`);
  }

  // --- Roles ---

  getRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(`${this.apiUrl}/security/roles/`);
  }

  createRole(data: Partial<Role>): Observable<Role> {
    return this.http.post<Role>(`${this.apiUrl}/security/roles/`, data);
  }

  updateRole(id: number, data: Partial<Role>): Observable<Role> {
    return this.http.patch<Role>(`${this.apiUrl}/security/roles/${id}/`, data);
  }

  deleteRole(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/security/roles/${id}/`);
  }

  // --- Permissions ---

  getPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(`${this.apiUrl}/security/permissions/`);
  }

  // --- Scanners ---

  listScanners(): Observable<ScannerDevice[]> {
    return this.http.get<ScannerDevice[]>(`${this.apiUrl}/sources/scanners/`);
  }

  scan(
    deviceId: string,
    options: { dpi?: number; color_mode?: string; paper_size?: string } = {},
  ): Observable<{ task_id: string; message: string }> {
    return this.http.post<{ task_id: string; message: string }>(
      `${this.apiUrl}/sources/scanners/${deviceId}/scan/`,
      options,
    );
  }
}
