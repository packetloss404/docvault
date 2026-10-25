import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, forkJoin, map, of, switchMap } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  SignatureRequest,
  SignatureAuditEvent,
  PublicSigningInfo,
  SignatureField,
} from '../models/esignature.model';
import { getAllPages } from './pagination';

export interface SignatureRequestCreate {
  title: string;
  message?: string;
  signing_order?: 'sequential' | 'parallel';
  signers: { name: string; email: string; order: number; verification_method: 'none' | 'email' | 'sms' }[];
  fields: { signer_index: number; page: number; x: number; y: number; width: number; height: number; field_type: string; required: boolean; order: number }[];
}

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
    return getAllPages<SignatureRequest>(this.http, `${this.apiUrl}/`, httpParams).pipe(
      map((items) => items.filter((item) =>
        (!params['document'] || item.document === Number(params['document'])) &&
        (!params['status'] || item.status === params['status']))),
      switchMap((items) => items.length
        ? forkJoin(items.map((item) => Array.isArray(item.signers) ? of(item) : this.getRequest(item.id)))
        : of([])),
    );
  }

  getRequest(id: number): Observable<SignatureRequest> {
    return this.http.get<SignatureRequest & { fields_data?: SignatureField[] }>(`${this.apiUrl}/${id}/`).pipe(
      map((result) => ({ ...result, fields: result.fields_data ?? result.fields ?? [] })),
    );
  }

  createRequest(
    documentId: number,
    data: Partial<SignatureRequest> | SignatureRequestCreate,
  ): Observable<SignatureRequest> {
    return this.http.post<SignatureRequest>(
      `${environment.apiUrl}/documents/${documentId}/signature-request/`,
      data,
    );
  }

  sendRequest(id: number): Observable<SignatureRequest> {
    return this.http.post(`${this.apiUrl}/${id}/send/`, {}).pipe(switchMap(() => this.getRequest(id)));
  }

  cancelRequest(id: number): Observable<SignatureRequest> {
    return this.http.post(
      `${this.apiUrl}/${id}/cancel/`,
      {},
    ).pipe(switchMap(() => this.getRequest(id)));
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
    return this.http.get<PublicSigningInfo & { document_page_count?: number; signer_status?: string }>(`${this.signUrl}/${token}/`).pipe(
      map((result) => ({ ...result, page_count: result.document_page_count ?? result.page_count, status: result.signer_status ?? result.status })),
    );
  }

  getSigningPreviewUrl(token: string, page: number): string {
    return `${this.signUrl}/${encodeURIComponent(token)}/preview/?page=${page}`;
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
      { fields: fields.map((field) => ({ field_id: field.id, value: field.value })) },
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
