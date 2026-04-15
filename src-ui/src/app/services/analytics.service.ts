import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  SearchAnalytics,
  SearchCuration,
  SearchSynonym,
} from '../models/analytics.model';

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Analytics ---

  getAnalytics(days: number = 30): Observable<SearchAnalytics> {
    const params = new HttpParams().set('days', days.toString());
    return this.http.get<SearchAnalytics>(
      `${this.baseUrl}/search/analytics/`,
      { params },
    );
  }

  trackClick(data: {
    query: string;
    document_id: number;
    position: number;
  }): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/search/click/`, data);
  }

  trackQuery(data: {
    query: string;
    response_time_ms: number;
    result_count: number;
  }): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/search/query-log/`, data);
  }

  // --- Synonyms ---

  getSynonyms(): Observable<PaginatedResponse<SearchSynonym>> {
    return this.http.get<PaginatedResponse<SearchSynonym>>(
      `${this.baseUrl}/search/synonyms/`,
    );
  }

  createSynonym(data: Partial<SearchSynonym>): Observable<SearchSynonym> {
    return this.http.post<SearchSynonym>(
      `${this.baseUrl}/search/synonyms/`,
      data,
    );
  }

  updateSynonym(
    id: number,
    data: Partial<SearchSynonym>,
  ): Observable<SearchSynonym> {
    return this.http.patch<SearchSynonym>(
      `${this.baseUrl}/search/synonyms/${id}/`,
      data,
    );
  }

  deleteSynonym(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/search/synonyms/${id}/`);
  }

  // --- Curations ---

  getCurations(): Observable<PaginatedResponse<SearchCuration>> {
    return this.http.get<PaginatedResponse<SearchCuration>>(
      `${this.baseUrl}/search/curations/`,
    );
  }

  createCuration(
    data: Partial<SearchCuration>,
  ): Observable<SearchCuration> {
    return this.http.post<SearchCuration>(
      `${this.baseUrl}/search/curations/`,
      data,
    );
  }

  updateCuration(
    id: number,
    data: Partial<SearchCuration>,
  ): Observable<SearchCuration> {
    return this.http.patch<SearchCuration>(
      `${this.baseUrl}/search/curations/${id}/`,
      data,
    );
  }

  deleteCuration(id: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/search/curations/${id}/`,
    );
  }
}
