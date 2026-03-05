import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  SemanticSearchResponse,
  ChatRequest,
  ChatResponse,
  SummaryResponse,
  EntityResponse,
  TitleSuggestion,
  AIConfig,
  AIStatus,
} from '../models/ai.model';

@Injectable({ providedIn: 'root' })
export class AIService {
  private baseUrl = `${environment.apiUrl}/ai`;

  constructor(private http: HttpClient) {}

  semanticSearch(query: string, k: number = 10): Observable<SemanticSearchResponse> {
    const params = new HttpParams().set('query', query).set('k', k.toString());
    return this.http.get<SemanticSearchResponse>(`${this.baseUrl}/search/semantic/`, { params });
  }

  hybridSearch(query: string, k: number = 10): Observable<SemanticSearchResponse> {
    const params = new HttpParams().set('query', query).set('k', k.toString());
    return this.http.get<SemanticSearchResponse>(`${this.baseUrl}/search/hybrid/`, { params });
  }

  similarDocuments(documentId: number, k: number = 10): Observable<SemanticSearchResponse> {
    const params = new HttpParams().set('k', k.toString());
    return this.http.get<SemanticSearchResponse>(`${this.baseUrl}/similar/${documentId}/`, { params });
  }

  chatWithDocument(documentId: number, request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.baseUrl}/documents/${documentId}/chat/`, request);
  }

  globalChat(request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.baseUrl}/chat/`, request);
  }

  summarize(documentId: number): Observable<SummaryResponse> {
    return this.http.get<SummaryResponse>(`${this.baseUrl}/documents/${documentId}/summarize/`);
  }

  extractEntities(documentId: number): Observable<EntityResponse> {
    return this.http.get<EntityResponse>(`${this.baseUrl}/documents/${documentId}/entities/`);
  }

  suggestTitle(documentId: number): Observable<TitleSuggestion> {
    return this.http.get<TitleSuggestion>(`${this.baseUrl}/documents/${documentId}/suggest-title/`);
  }

  getConfig(): Observable<AIConfig> {
    return this.http.get<AIConfig>(`${this.baseUrl}/config/`);
  }

  getStatus(): Observable<AIStatus> {
    return this.http.get<AIStatus>(`${this.baseUrl}/status/`);
  }

  rebuildIndex(): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.baseUrl}/rebuild-index/`, {});
  }
}
