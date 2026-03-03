import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  AutocompleteItem,
  Cabinet,
  CabinetTreeNode,
  Correspondent,
  CustomField,
  CustomFieldInstance,
  DocumentMetadata,
  DocumentTypeCustomField,
  DocumentTypeMetadata,
  MetadataType,
  StoragePath,
  Tag,
  TagTreeNode,
} from '../models/organization.model';

@Injectable({ providedIn: 'root' })
export class OrganizationService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Tags ---

  getTags(): Observable<PaginatedResponse<Tag>> {
    return this.http.get<PaginatedResponse<Tag>>(`${this.baseUrl}/tags/`);
  }

  getTagTree(): Observable<TagTreeNode[]> {
    return this.http.get<TagTreeNode[]>(`${this.baseUrl}/tags/tree/`);
  }

  getTag(id: number): Observable<Tag> {
    return this.http.get<Tag>(`${this.baseUrl}/tags/${id}/`);
  }

  createTag(data: Partial<Tag>): Observable<Tag> {
    return this.http.post<Tag>(`${this.baseUrl}/tags/`, data);
  }

  updateTag(id: number, data: Partial<Tag>): Observable<Tag> {
    return this.http.patch<Tag>(`${this.baseUrl}/tags/${id}/`, data);
  }

  deleteTag(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/tags/${id}/`);
  }

  autocompleteTag(q: string): Observable<AutocompleteItem[]> {
    return this.http.get<AutocompleteItem[]>(
      `${this.baseUrl}/tags/autocomplete/`,
      { params: new HttpParams().set('q', q) },
    );
  }

  // --- Correspondents ---

  getCorrespondents(): Observable<PaginatedResponse<Correspondent>> {
    return this.http.get<PaginatedResponse<Correspondent>>(
      `${this.baseUrl}/correspondents/`,
    );
  }

  createCorrespondent(data: Partial<Correspondent>): Observable<Correspondent> {
    return this.http.post<Correspondent>(
      `${this.baseUrl}/correspondents/`,
      data,
    );
  }

  updateCorrespondent(id: number, data: Partial<Correspondent>): Observable<Correspondent> {
    return this.http.patch<Correspondent>(
      `${this.baseUrl}/correspondents/${id}/`,
      data,
    );
  }

  deleteCorrespondent(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/correspondents/${id}/`);
  }

  autocompleteCorrespondent(q: string): Observable<AutocompleteItem[]> {
    return this.http.get<AutocompleteItem[]>(
      `${this.baseUrl}/correspondents/autocomplete/`,
      { params: new HttpParams().set('q', q) },
    );
  }

  // --- Cabinets ---

  getCabinets(): Observable<PaginatedResponse<Cabinet>> {
    return this.http.get<PaginatedResponse<Cabinet>>(
      `${this.baseUrl}/cabinets/`,
    );
  }

  getCabinetTree(): Observable<CabinetTreeNode[]> {
    return this.http.get<CabinetTreeNode[]>(
      `${this.baseUrl}/cabinets/tree/`,
    );
  }

  createCabinet(data: Partial<Cabinet>): Observable<Cabinet> {
    return this.http.post<Cabinet>(`${this.baseUrl}/cabinets/`, data);
  }

  updateCabinet(id: number, data: Partial<Cabinet>): Observable<Cabinet> {
    return this.http.patch<Cabinet>(`${this.baseUrl}/cabinets/${id}/`, data);
  }

  deleteCabinet(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/cabinets/${id}/`);
  }

  moveCabinet(id: number, parentId: number | null): Observable<Cabinet> {
    return this.http.post<Cabinet>(
      `${this.baseUrl}/cabinets/${id}/move/`,
      { parent: parentId },
    );
  }

  autocompleteCabinet(q: string): Observable<AutocompleteItem[]> {
    return this.http.get<AutocompleteItem[]>(
      `${this.baseUrl}/cabinets/autocomplete/`,
      { params: new HttpParams().set('q', q) },
    );
  }

  // --- Storage Paths ---

  getStoragePaths(): Observable<PaginatedResponse<StoragePath>> {
    return this.http.get<PaginatedResponse<StoragePath>>(
      `${this.baseUrl}/storage-paths/`,
    );
  }

  createStoragePath(data: Partial<StoragePath>): Observable<StoragePath> {
    return this.http.post<StoragePath>(`${this.baseUrl}/storage-paths/`, data);
  }

  updateStoragePath(id: number, data: Partial<StoragePath>): Observable<StoragePath> {
    return this.http.patch<StoragePath>(
      `${this.baseUrl}/storage-paths/${id}/`,
      data,
    );
  }

  deleteStoragePath(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/storage-paths/${id}/`);
  }

  // --- Custom Fields ---

  getCustomFields(): Observable<PaginatedResponse<CustomField>> {
    return this.http.get<PaginatedResponse<CustomField>>(
      `${this.baseUrl}/custom-fields/`,
    );
  }

  getCustomField(id: number): Observable<CustomField> {
    return this.http.get<CustomField>(`${this.baseUrl}/custom-fields/${id}/`);
  }

  createCustomField(data: Partial<CustomField>): Observable<CustomField> {
    return this.http.post<CustomField>(`${this.baseUrl}/custom-fields/`, data);
  }

  updateCustomField(id: number, data: Partial<CustomField>): Observable<CustomField> {
    return this.http.patch<CustomField>(
      `${this.baseUrl}/custom-fields/${id}/`,
      data,
    );
  }

  deleteCustomField(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/custom-fields/${id}/`);
  }

  // --- Custom Field Instances (per-document) ---

  getDocumentCustomFields(docId: number): Observable<CustomFieldInstance[]> {
    return this.http.get<CustomFieldInstance[]>(
      `${this.baseUrl}/documents/${docId}/custom-fields/`,
    );
  }

  setDocumentCustomField(
    docId: number,
    fieldId: number,
    value: unknown,
  ): Observable<CustomFieldInstance> {
    return this.http.post<CustomFieldInstance>(
      `${this.baseUrl}/documents/${docId}/custom-fields/`,
      { document: docId, field: fieldId, value },
    );
  }

  updateDocumentCustomField(
    docId: number,
    instanceId: number,
    value: unknown,
  ): Observable<CustomFieldInstance> {
    return this.http.patch<CustomFieldInstance>(
      `${this.baseUrl}/documents/${docId}/custom-fields/${instanceId}/`,
      { value },
    );
  }

  deleteDocumentCustomField(docId: number, instanceId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/documents/${docId}/custom-fields/${instanceId}/`,
    );
  }

  // --- Metadata Types ---

  getMetadataTypes(): Observable<PaginatedResponse<MetadataType>> {
    return this.http.get<PaginatedResponse<MetadataType>>(
      `${this.baseUrl}/metadata-types/`,
    );
  }

  getMetadataType(id: number): Observable<MetadataType> {
    return this.http.get<MetadataType>(`${this.baseUrl}/metadata-types/${id}/`);
  }

  createMetadataType(data: Partial<MetadataType>): Observable<MetadataType> {
    return this.http.post<MetadataType>(
      `${this.baseUrl}/metadata-types/`,
      data,
    );
  }

  updateMetadataType(id: number, data: Partial<MetadataType>): Observable<MetadataType> {
    return this.http.patch<MetadataType>(
      `${this.baseUrl}/metadata-types/${id}/`,
      data,
    );
  }

  deleteMetadataType(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/metadata-types/${id}/`);
  }

  getMetadataTypeLookupOptions(id: number): Observable<{ options: string[] }> {
    return this.http.get<{ options: string[] }>(
      `${this.baseUrl}/metadata-types/${id}/lookup-options/`,
    );
  }

  // --- Document Metadata (per-document) ---

  getDocumentMetadata(docId: number): Observable<DocumentMetadata[]> {
    return this.http.get<DocumentMetadata[]>(
      `${this.baseUrl}/documents/${docId}/metadata/`,
    );
  }

  setDocumentMetadata(
    docId: number,
    metadataTypeId: number,
    value: string,
  ): Observable<DocumentMetadata> {
    return this.http.post<DocumentMetadata>(
      `${this.baseUrl}/documents/${docId}/metadata/`,
      { document: docId, metadata_type: metadataTypeId, value },
    );
  }

  updateDocumentMetadata(
    docId: number,
    instanceId: number,
    value: string,
  ): Observable<DocumentMetadata> {
    return this.http.patch<DocumentMetadata>(
      `${this.baseUrl}/documents/${docId}/metadata/${instanceId}/`,
      { value },
    );
  }

  deleteDocumentMetadata(docId: number, instanceId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/documents/${docId}/metadata/${instanceId}/`,
    );
  }

  // --- Document Type Assignments ---

  getDocTypeCustomFields(
    docTypeId: number,
  ): Observable<DocumentTypeCustomField[]> {
    return this.http.get<DocumentTypeCustomField[]>(
      `${this.baseUrl}/document-types/${docTypeId}/custom-fields/`,
    );
  }

  assignDocTypeCustomField(
    docTypeId: number,
    fieldId: number,
    required: boolean,
  ): Observable<DocumentTypeCustomField> {
    return this.http.post<DocumentTypeCustomField>(
      `${this.baseUrl}/document-types/${docTypeId}/custom-fields/`,
      { document_type: docTypeId, custom_field: fieldId, required },
    );
  }

  removeDocTypeCustomField(docTypeId: number, assignmentId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/document-types/${docTypeId}/custom-fields/${assignmentId}/`,
    );
  }

  getDocTypeMetadata(
    docTypeId: number,
  ): Observable<DocumentTypeMetadata[]> {
    return this.http.get<DocumentTypeMetadata[]>(
      `${this.baseUrl}/document-types/${docTypeId}/metadata-types/`,
    );
  }

  assignDocTypeMetadata(
    docTypeId: number,
    metadataTypeId: number,
    required: boolean,
  ): Observable<DocumentTypeMetadata> {
    return this.http.post<DocumentTypeMetadata>(
      `${this.baseUrl}/document-types/${docTypeId}/metadata-types/`,
      { document_type: docTypeId, metadata_type: metadataTypeId, required },
    );
  }

  removeDocTypeMetadata(docTypeId: number, assignmentId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/document-types/${docTypeId}/metadata-types/${assignmentId}/`,
    );
  }

  // --- Bulk Operations ---

  bulkAssign(data: {
    document_ids: number[];
    tag_ids?: number[];
    remove_tag_ids?: number[];
    correspondent_id?: number | null;
    cabinet_id?: number | null;
  }): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(
      `${this.baseUrl}/bulk-assign/`,
      data,
    );
  }

  bulkSetCustomField(data: {
    document_ids: number[];
    field_id: number;
    value: unknown;
  }): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(
      `${this.baseUrl}/bulk-set-custom-fields/`,
      data,
    );
  }
}
