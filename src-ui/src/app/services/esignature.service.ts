import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  SignatureRequest,
  SignatureAuditEvent,
  PublicSigningInfo,
  SignatureField,
} from '../models/esignature.model';

@Injectable({ providedIn: 'root' })
export class EsignatureService {
  private readonly apiUrl = `${environment.apiUrl}/signature-requests`;
  private readonly signUrl = `${environment.apiUrl}/sign`;

  constructor(private http: HttpClient) {}

  // --- Authenticated endpoints ---

  getRequests(
    params: Record<string, string> = {},
  ): Observable<SignatureRequest[]> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value);
      }
    }
    return this.http.get<SignatureRequest[]>(`${this.apiUrl}/`, {
      params: httpParams,
    });
  }

  getRequest(id: number): Observable<SignatureRequest> {
    return this.http.get<SignatureRequest>(`${this.apiUrl}/${id}/`);
  }

  createRequest(
    documentId: number,
    data: Partial<SignatureRequest>,
  ): Observable<SignatureRequest> {
    return this.http.post<SignatureRequest>(
      `${environment.apiUrl}/documents/${documentId}/signature-request/`,
      data,
    );
  }

  sendRequest(id: number): Observable<SignatureRequest> {
    return this.http.post<SignatureRequest>(`${this.apiUrl}/${id}/send/`, {});
  }

  cancelRequest(id: number): Observable<SignatureRequest> {
    return this.http.post<SignatureRequest>(
      `${this.apiUrl}/${id}/cancel/`,
      {},
    );
  }

  remindSigners(id: number): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${this.apiUrl}/${id}/remind/`,
      {},
    );
  }

  getAuditTrail(id: number): Observable<SignatureAuditEvent[]> {
    return this.http.get<SignatureAuditEvent[]>(`${this.apiUrl}/${id}/audit/`);
  }

  downloadCertificate(id: number): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${id}/certificate/`, {
      responseType: 'blob',
    });
  }

  // --- Public signing endpoints (no auth header) ---

  getSigningInfo(token: string): Observable<PublicSigningInfo> {
    return this.http.get<PublicSigningInfo>(`${this.signUrl}/${token}/`);
  }

  recordPageView(
    token: string,
    page: number,
  ): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${this.signUrl}/${token}/view_page/`,
      { page },
    );
  }

  completeSigning(
    token: string,
    fields: Partial<SignatureField>[],
  ): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${this.signUrl}/${token}/complete/`,
      { fields },
    );
  }

  declineSigning(
    token: string,
    reason: string,
  ): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${this.signUrl}/${token}/decline/`,
      { reason },
    );
  }
}
