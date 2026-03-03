import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  AutocompleteResult,
  SavedView,
  SavedViewListItem,
  SearchResponse,
} from '../models/search.model';

@Injectable({ providedIn: 'root' })
export class SearchService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Full-text Search ---

  search(params: {
    query?: string;
    page?: number;
    page_size?: number;
    document_type_id?: number;
    correspondent_id?: number;
    tag_ids?: number[];
    created_after?: string;
    created_before?: string;
  }): Observable<SearchResponse> {
    let httpParams = new HttpParams();
    if (params.query) httpParams = httpParams.set('query', params.query);
    if (params.page) httpParams = httpParams.set('page', params.page.toString());
    if (params.page_size)
      httpParams = httpParams.set('page_size', params.page_size.toString());
    if (params.document_type_id)
      httpParams = httpParams.set(
        'document_type_id',
        params.document_type_id.toString(),
      );
    if (params.correspondent_id)
      httpParams = httpParams.set(
        'correspondent_id',
        params.correspondent_id.toString(),
      );
    if (params.tag_ids && params.tag_ids.length)
      httpParams = httpParams.set('tag_ids', params.tag_ids.join(','));
    if (params.created_after)
      httpParams = httpParams.set('created_after', params.created_after);
    if (params.created_before)
      httpParams = httpParams.set('created_before', params.created_before);

    return this.http.get<SearchResponse>(`${this.baseUrl}/search/`, {
      params: httpParams,
    });
  }

  autocomplete(query: string): Observable<AutocompleteResult[]> {
    return this.http.get<AutocompleteResult[]>(
      `${this.baseUrl}/search/autocomplete/`,
      { params: new HttpParams().set('query', query) },
    );
  }

  similarDocuments(id: number): Observable<AutocompleteResult[]> {
    return this.http.get<AutocompleteResult[]>(
      `${this.baseUrl}/search/similar/${id}/`,
    );
  }

  // --- Saved Views ---

  getSavedViews(): Observable<PaginatedResponse<SavedViewListItem>> {
    return this.http.get<PaginatedResponse<SavedViewListItem>>(
      `${this.baseUrl}/saved-views/`,
    );
  }

  getSavedView(id: number): Observable<SavedView> {
    return this.http.get<SavedView>(`${this.baseUrl}/saved-views/${id}/`);
  }

  createSavedView(data: Partial<SavedView>): Observable<SavedView> {
    return this.http.post<SavedView>(`${this.baseUrl}/saved-views/`, data);
  }

  updateSavedView(id: number, data: Partial<SavedView>): Observable<SavedView> {
    return this.http.patch<SavedView>(
      `${this.baseUrl}/saved-views/${id}/`,
      data,
    );
  }

  deleteSavedView(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/saved-views/${id}/`);
  }

  executeSavedView(
    id: number,
    page?: number,
  ): Observable<PaginatedResponse<unknown>> {
    let params = new HttpParams();
    if (page) params = params.set('page', page.toString());
    return this.http.get<PaginatedResponse<unknown>>(
      `${this.baseUrl}/saved-views/${id}/execute/`,
      { params },
    );
  }

  getDashboardViews(): Observable<SavedViewListItem[]> {
    return this.http.get<SavedViewListItem[]>(
      `${this.baseUrl}/saved-views/dashboard/`,
    );
  }

  getSidebarViews(): Observable<SavedViewListItem[]> {
    return this.http.get<SavedViewListItem[]>(
      `${this.baseUrl}/saved-views/sidebar/`,
    );
  }
}
