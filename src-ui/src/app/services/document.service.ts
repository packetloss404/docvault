import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Document,
  DocumentType,
  DocumentVersion,
  PaginatedResponse,
} from '../models/document.model';

export interface DocumentQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  ordering?: string;
  document_type?: number;
  language?: string;
  mime_type?: string;
  created_after?: string;
  created_before?: string;
  has_asn?: boolean;
}

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private readonly apiUrl = `${environment.apiUrl}/documents`;
  private readonly typesUrl = `${environment.apiUrl}/document-types`;

  constructor(private http: HttpClient) {}

  // --- Documents ---

  getDocuments(
    params: DocumentQueryParams = {},
  ): Observable<PaginatedResponse<Document>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<PaginatedResponse<Document>>(`${this.apiUrl}/`, {
      params: httpParams,
    });
  }

  getDocument(id: number): Observable<Document> {
    return this.http.get<Document>(`${this.apiUrl}/${id}/`);
  }

  createDocument(data: Partial<Document>): Observable<Document> {
    return this.http.post<Document>(`${this.apiUrl}/`, data);
  }

  updateDocument(id: number, data: Partial<Document>): Observable<Document> {
    return this.http.patch<Document>(`${this.apiUrl}/${id}/`, data);
  }

  deleteDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`);
  }

  restoreDocument(id: number): Observable<Document> {
    return this.http.post<Document>(`${this.apiUrl}/${id}/restore/`, {});
  }

  getDeletedDocuments(): Observable<PaginatedResponse<Document>> {
    return this.http.get<PaginatedResponse<Document>>(
      `${this.apiUrl}/deleted/`,
    );
  }

  // --- Preview & Download ---

  getPreviewUrl(id: number): string {
    return `${this.apiUrl}/${id}/preview/`;
  }

  getDownloadUrl(id: number, version: 'original' | 'archive' = 'original'): string {
    return `${this.apiUrl}/${id}/download/?version=${version}`;
  }

  // --- Versions ---

  getVersions(documentId: number): Observable<DocumentVersion[]> {
    return this.http.get<DocumentVersion[]>(
      `${this.apiUrl}/${documentId}/versions/`,
    );
  }

  activateVersion(documentId: number, versionId: number): Observable<DocumentVersion> {
    return this.http.post<DocumentVersion>(
      `${this.apiUrl}/${documentId}/versions/${versionId}/activate/`,
      {},
    );
  }

  compareVersions(
    documentId: number,
    v1: number,
    v2: number,
  ): Observable<{ v1: DocumentVersion; v2: DocumentVersion; diff_html: string }> {
    return this.http.get<{ v1: DocumentVersion; v2: DocumentVersion; diff_html: string }>(
      `${this.apiUrl}/${documentId}/versions/compare/`,
      { params: { v1: String(v1), v2: String(v2) } },
    );
  }

  uploadNewVersion(
    documentId: number,
    file: File,
    comment: string = '',
  ): Observable<DocumentVersion> {
    const formData = new FormData();
    formData.append('document', file);
    if (comment) {
      formData.append('comment', comment);
    }
    return this.http.post<DocumentVersion>(
      `${this.apiUrl}/${documentId}/files/`,
      formData,
    );
  }

  // --- Document Types ---

  getDocumentTypes(): Observable<PaginatedResponse<DocumentType>> {
    return this.http.get<PaginatedResponse<DocumentType>>(`${this.typesUrl}/`);
  }

  getDocumentType(id: number): Observable<DocumentType> {
    return this.http.get<DocumentType>(`${this.typesUrl}/${id}/`);
  }

  createDocumentType(data: Partial<DocumentType>): Observable<DocumentType> {
    return this.http.post<DocumentType>(`${this.typesUrl}/`, data);
  }

  updateDocumentType(
    id: number,
    data: Partial<DocumentType>,
  ): Observable<DocumentType> {
    return this.http.patch<DocumentType>(`${this.typesUrl}/${id}/`, data);
  }

  deleteDocumentType(id: number): Observable<void> {
    return this.http.delete<void>(`${this.typesUrl}/${id}/`);
  }

  // --- Bulk Operations ---

  bulkOperation(data: {
    action: string;
    document_ids: number[];
    tag_ids?: number[];
    correspondent_id?: number | null;
    document_type_id?: number | null;
  }): Observable<{ affected: number }> {
    return this.http.post<{ affected: number }>(
      `${environment.apiUrl}/bulk/`,
      data,
    );
  }
}
