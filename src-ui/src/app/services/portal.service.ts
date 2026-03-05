import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  PortalConfig,
  DocumentRequest,
  PortalSubmission,
  PublicPortalInfo,
  PublicRequestInfo,
} from '../models/portal.model';
import { PaginatedResponse } from '../models/document.model';

@Injectable({ providedIn: 'root' })
export class PortalService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Portal Admin ---

  getPortals(): Observable<PaginatedResponse<PortalConfig>> {
    return this.http.get<PaginatedResponse<PortalConfig>>(
      `${this.apiUrl}/portals/`,
    );
  }

  getPortal(id: number): Observable<PortalConfig> {
    return this.http.get<PortalConfig>(`${this.apiUrl}/portals/${id}/`);
  }

  createPortal(data: Partial<PortalConfig>): Observable<PortalConfig> {
    return this.http.post<PortalConfig>(`${this.apiUrl}/portals/`, data);
  }

  updatePortal(
    id: number,
    data: Partial<PortalConfig>,
  ): Observable<PortalConfig> {
    return this.http.patch<PortalConfig>(
      `${this.apiUrl}/portals/${id}/`,
      data,
    );
  }

  deletePortal(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/portals/${id}/`);
  }

  // --- Document Requests ---

  getRequests(): Observable<PaginatedResponse<DocumentRequest>> {
    return this.http.get<PaginatedResponse<DocumentRequest>>(
      `${this.apiUrl}/document-requests/`,
    );
  }

  createRequest(data: Partial<DocumentRequest>): Observable<DocumentRequest> {
    return this.http.post<DocumentRequest>(
      `${this.apiUrl}/document-requests/`,
      data,
    );
  }

  sendRequest(id: number): Observable<DocumentRequest> {
    return this.http.post<DocumentRequest>(
      `${this.apiUrl}/document-requests/${id}/send/`,
      {},
    );
  }

  remindRequest(id: number): Observable<DocumentRequest> {
    return this.http.post<DocumentRequest>(
      `${this.apiUrl}/document-requests/${id}/remind/`,
      {},
    );
  }

  // --- Submissions ---

  getSubmissions(params: {
    portal?: number;
    status?: string;
  } = {}): Observable<PaginatedResponse<PortalSubmission>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<PaginatedResponse<PortalSubmission>>(
      `${this.apiUrl}/portal-submissions/`,
      { params: httpParams },
    );
  }

  reviewSubmission(
    id: number,
    data: { status: string; review_notes?: string },
  ): Observable<PortalSubmission> {
    return this.http.patch<PortalSubmission>(
      `${this.apiUrl}/portal-submissions/${id}/review/`,
      data,
    );
  }

  // --- Public Endpoints ---

  getPublicPortal(slug: string): Observable<PublicPortalInfo> {
    return this.http.get<PublicPortalInfo>(`${this.apiUrl}/portal/${slug}/`);
  }

  publicUpload(slug: string, formData: FormData): Observable<{ id: number }> {
    return this.http.post<{ id: number }>(
      `${this.apiUrl}/portal/${slug}/upload/`,
      formData,
    );
  }

  getPublicRequest(token: string): Observable<PublicRequestInfo> {
    return this.http.get<PublicRequestInfo>(
      `${this.apiUrl}/request/${token}/`,
    );
  }

  publicRequestUpload(
    token: string,
    formData: FormData,
  ): Observable<{ id: number }> {
    return this.http.post<{ id: number }>(
      `${this.apiUrl}/request/${token}/upload/`,
      formData,
    );
  }
}
