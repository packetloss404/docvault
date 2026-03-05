import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ClassifierStatus, Suggestions } from '../models/ml.model';
import { Document } from '../models/document.model';

@Injectable({ providedIn: 'root' })
export class MlService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getSuggestions(documentId: number): Observable<Suggestions> {
    return this.http.get<Suggestions>(
      `${this.apiUrl}/documents/${documentId}/suggestions/`,
    );
  }

  getClassifierStatus(): Observable<ClassifierStatus> {
    return this.http.get<ClassifierStatus>(
      `${this.apiUrl}/classifier/status/`,
    );
  }

  triggerTraining(): Observable<{ task_id: string }> {
    return this.http.post<{ task_id: string }>(
      `${this.apiUrl}/classifier/train/`,
      {},
    );
  }

  applyTag(documentId: number, tagId: number): Observable<Document> {
    return this.http.post<Document>(
      `${this.apiUrl}/documents/${documentId}/tags/`,
      { tag: tagId },
    );
  }

  applyCorrespondent(
    documentId: number,
    correspondentId: number,
  ): Observable<Document> {
    return this.http.patch<Document>(
      `${this.apiUrl}/documents/${documentId}/`,
      { correspondent: correspondentId },
    );
  }

  applyDocumentType(
    documentId: number,
    typeId: number,
  ): Observable<Document> {
    return this.http.patch<Document>(
      `${this.apiUrl}/documents/${documentId}/`,
      { document_type: typeId },
    );
  }

  applyStoragePath(
    documentId: number,
    pathId: number,
  ): Observable<Document> {
    return this.http.patch<Document>(
      `${this.apiUrl}/documents/${documentId}/`,
      { storage_path: pathId },
    );
  }
}
