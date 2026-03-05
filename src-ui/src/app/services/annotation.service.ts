import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Annotation, AnnotationReply } from '../models/annotation.model';

@Injectable({ providedIn: 'root' })
export class AnnotationService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  private annotationsUrl(documentId: number): string {
    return `${this.apiUrl}/documents/${documentId}/annotations`;
  }

  getAnnotations(
    documentId: number,
    params: Record<string, string> = {},
  ): Observable<Annotation[]> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value);
      }
    }
    return this.http.get<Annotation[]>(`${this.annotationsUrl(documentId)}/`, {
      params: httpParams,
    });
  }

  createAnnotation(
    documentId: number,
    data: Partial<Annotation>,
  ): Observable<Annotation> {
    return this.http.post<Annotation>(
      `${this.annotationsUrl(documentId)}/`,
      data,
    );
  }

  updateAnnotation(
    documentId: number,
    annotationId: number,
    data: Partial<Annotation>,
  ): Observable<Annotation> {
    return this.http.patch<Annotation>(
      `${this.annotationsUrl(documentId)}/${annotationId}/`,
      data,
    );
  }

  deleteAnnotation(
    documentId: number,
    annotationId: number,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.annotationsUrl(documentId)}/${annotationId}/`,
    );
  }

  getReplies(
    documentId: number,
    annotationId: number,
  ): Observable<AnnotationReply[]> {
    return this.http.get<AnnotationReply[]>(
      `${this.annotationsUrl(documentId)}/${annotationId}/replies/`,
    );
  }

  createReply(
    documentId: number,
    annotationId: number,
    text: string,
  ): Observable<AnnotationReply> {
    return this.http.post<AnnotationReply>(
      `${this.annotationsUrl(documentId)}/${annotationId}/replies/`,
      { text },
    );
  }

  exportAnnotations(
    documentId: number,
  ): Observable<{ document_id: number; annotation_count: number; annotations: Annotation[] }> {
    return this.http.post<{
      document_id: number;
      annotation_count: number;
      annotations: Annotation[];
    }>(`${this.annotationsUrl(documentId)}/export/`, {});
  }
}
