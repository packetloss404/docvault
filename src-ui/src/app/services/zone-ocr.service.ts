import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  ZoneOCRTemplate,
  ZoneOCRField,
  ZoneOCRResult,
} from '../models/zone-ocr.model';

@Injectable({ providedIn: 'root' })
export class ZoneOCRService {
  private readonly baseUrl = `${environment.apiUrl}/zone-ocr-templates`;
  private readonly resultsUrl = `${environment.apiUrl}/zone-ocr-results`;

  constructor(private http: HttpClient) {}

  // --- Templates ---

  getTemplates(): Observable<PaginatedResponse<ZoneOCRTemplate>> {
    return this.http.get<PaginatedResponse<ZoneOCRTemplate>>(
      `${this.baseUrl}/`,
    );
  }

  getTemplate(id: number): Observable<ZoneOCRTemplate> {
    return this.http.get<ZoneOCRTemplate>(`${this.baseUrl}/${id}/`);
  }

  createTemplate(
    data: Partial<ZoneOCRTemplate>,
  ): Observable<ZoneOCRTemplate> {
    return this.http.post<ZoneOCRTemplate>(`${this.baseUrl}/`, data);
  }

  updateTemplate(
    id: number,
    data: Partial<ZoneOCRTemplate>,
  ): Observable<ZoneOCRTemplate> {
    return this.http.patch<ZoneOCRTemplate>(`${this.baseUrl}/${id}/`, data);
  }

  deleteTemplate(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}/`);
  }

  // --- Fields ---

  getFields(templateId: number): Observable<ZoneOCRField[]> {
    return this.http.get<ZoneOCRField[]>(
      `${this.baseUrl}/${templateId}/fields/`,
    );
  }

  createField(
    templateId: number,
    data: Partial<ZoneOCRField>,
  ): Observable<ZoneOCRField> {
    return this.http.post<ZoneOCRField>(
      `${this.baseUrl}/${templateId}/fields/`,
      data,
    );
  }

  updateField(
    templateId: number,
    fieldId: number,
    data: Partial<ZoneOCRField>,
  ): Observable<ZoneOCRField> {
    return this.http.patch<ZoneOCRField>(
      `${this.baseUrl}/${templateId}/fields/${fieldId}/`,
      data,
    );
  }

  deleteField(templateId: number, fieldId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}/fields/${fieldId}/`,
    );
  }

  // --- Test ---

  testTemplate(
    templateId: number,
    documentId: number,
  ): Observable<ZoneOCRResult[]> {
    return this.http.post<ZoneOCRResult[]>(
      `${this.baseUrl}/${templateId}/test/`,
      { document_id: documentId },
    );
  }

  // --- Results ---

  getResults(params: {
    template?: number;
    min_confidence?: number;
    max_confidence?: number;
    reviewed?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Observable<PaginatedResponse<ZoneOCRResult>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<PaginatedResponse<ZoneOCRResult>>(
      `${this.resultsUrl}/`,
      { params: httpParams },
    );
  }

  correctResult(
    id: number,
    data: { corrected_value: string; reviewed: boolean },
  ): Observable<ZoneOCRResult> {
    return this.http.patch<ZoneOCRResult>(`${this.resultsUrl}/${id}/`, data);
  }
}
