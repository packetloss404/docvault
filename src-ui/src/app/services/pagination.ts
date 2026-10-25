import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, Observable, expand, reduce } from 'rxjs';
import { PaginatedResponse } from '../models/document.model';

export function getAllPages<T>(http: HttpClient, url: string, params?: HttpParams): Observable<T[]> {
  return http.get<T[] | PaginatedResponse<T>>(url, { params }).pipe(
    expand((response) => !Array.isArray(response) && response.next
      ? http.get<T[] | PaginatedResponse<T>>(response.next) : EMPTY),
    reduce((items, response) => [...items, ...(Array.isArray(response) ? response : response.results)], [] as T[]),
  );
}
