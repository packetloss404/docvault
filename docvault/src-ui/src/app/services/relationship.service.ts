import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  RelationshipType,
  DocumentRelationship,
  RelationshipGraph,
} from '../models/relationship.model';

@Injectable({ providedIn: 'root' })
export class RelationshipService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Relationship Types ---

  getRelationshipTypes(): Observable<RelationshipType[]> {
    return this.http.get<RelationshipType[]>(
      `${this.apiUrl}/relationship-types/`,
    );
  }

  createRelationshipType(
    data: Partial<RelationshipType>,
  ): Observable<RelationshipType> {
    return this.http.post<RelationshipType>(
      `${this.apiUrl}/relationship-types/`,
      data,
    );
  }

  // --- Document Relationships ---

  getDocumentRelationships(
    documentId: number,
  ): Observable<DocumentRelationship[]> {
    return this.http.get<DocumentRelationship[]>(
      `${this.apiUrl}/documents/${documentId}/relationships/`,
    );
  }

  createDocumentRelationship(
    documentId: number,
    data: Partial<DocumentRelationship>,
  ): Observable<DocumentRelationship> {
    return this.http.post<DocumentRelationship>(
      `${this.apiUrl}/documents/${documentId}/relationships/`,
      data,
    );
  }

  deleteDocumentRelationship(
    documentId: number,
    relId: number,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/documents/${documentId}/relationships/${relId}/`,
    );
  }

  // --- Relationship Graph ---

  getRelationshipGraph(
    documentId: number,
    depth: number = 1,
  ): Observable<RelationshipGraph> {
    const params = new HttpParams().set('depth', depth.toString());
    return this.http.get<RelationshipGraph>(
      `${this.apiUrl}/documents/${documentId}/relationship-graph/`,
      { params },
    );
  }
}
