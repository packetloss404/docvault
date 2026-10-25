import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
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
    let httpParams = new HttpParams().set('aggregate', 'true');
    for (const [key, value] of Object.entries(params)) {
      if (key !== 'page' && key !== 'page_size' && value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key === 'search' ? 'value' : key, String(value));
      }
    }
    return this.http.get<(Omit<EntityAggregate, 'entity_type'> & { entity_type_name: string })[]>(
      `${this.baseUrl}/entities/`,
      { params: httpParams },
    ).pipe(map((entities) => {
      const page = Math.max(1, params.page ?? 1);
      const pageSize = Math.max(1, params.page_size ?? 25);
      return {
        count: entities.length,
        next: null,
        previous: null,
        results: entities.slice((page - 1) * pageSize, page * pageSize)
          .map((entity) => ({ ...entity, entity_type: entity.entity_type_name })),
      };
    }));
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
    return this.http.get<{ id?: number; document_id?: number; title: string }[]>(
      `${this.baseUrl}/entities/${entityType}/${encodeURIComponent(value)}/documents/`,
    ).pipe(map((documents) => documents.map((document) => ({
      document_id: document.document_id ?? document.id!, title: document.title,
    }))));
  }

  getCooccurrence(entityType: string, value: string): Observable<{ entity: EntityAggregate; count: number }[]> {
    return this.http.get<{ entity: EntityAggregate; count: number }[]>(
      `${this.baseUrl}/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(value)}/cooccurrence/`,
    );
  }
}
