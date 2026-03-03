import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  Entity,
  EntityAggregate,
  EntityType,
} from '../models/entity.model';

@Injectable({ providedIn: 'root' })
export class EntityService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getEntityTypes(): Observable<PaginatedResponse<EntityType>> {
    return this.http.get<PaginatedResponse<EntityType>>(
      `${this.baseUrl}/entity-types/`,
    );
  }

  getEntities(params: {
    entity_type?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}): Observable<PaginatedResponse<EntityAggregate>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<PaginatedResponse<EntityAggregate>>(
      `${this.baseUrl}/entities/`,
      { params: httpParams },
    );
  }

  getDocumentEntities(documentId: number): Observable<Entity[]> {
    return this.http.get<Entity[]>(
      `${this.baseUrl}/documents/${documentId}/entities/`,
    );
  }

  getEntityDocuments(
    entityType: string,
    value: string,
  ): Observable<{ document_id: number; title: string }[]> {
    return this.http.get<{ document_id: number; title: string }[]>(
      `${this.baseUrl}/entities/${entityType}/${encodeURIComponent(value)}/documents/`,
    );
  }
}
