import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { OrganizationService } from './organization.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

describe('OrganizationService', () => {
  let service: OrganizationService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(OrganizationService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  // --- Tags ---

  describe('getTags', () => {
    it('sends GET to /tags/', () => {
      service.getTags().subscribe();
      const req = httpTesting.expectOne(`${API}/tags/`);
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('getTagTree', () => {
    it('sends GET to /tags/tree/', () => {
      service.getTagTree().subscribe();
      const req = httpTesting.expectOne(`${API}/tags/tree/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getTag', () => {
    it('sends GET to /tags/:id/', () => {
      service.getTag(5).subscribe();
      const req = httpTesting.expectOne(`${API}/tags/5/`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 5, name: 'Test' });
    });
  });

  describe('createTag', () => {
    it('sends POST to /tags/ with payload', () => {
      const data = { name: 'Invoice' };
      service.createTag(data).subscribe();
      const req = httpTesting.expectOne(`${API}/tags/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateTag', () => {
    it('sends PATCH to /tags/:id/ with payload', () => {
      const data = { name: 'Updated' };
      service.updateTag(5, data).subscribe();
      const req = httpTesting.expectOne(`${API}/tags/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 5, ...data });
    });
  });

  describe('deleteTag', () => {
    it('sends DELETE to /tags/:id/', () => {
      service.deleteTag(5).subscribe();
      const req = httpTesting.expectOne(`${API}/tags/5/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('autocompleteTag', () => {
    it('sends GET to /tags/autocomplete/ with q param', () => {
      service.autocompleteTag('inv').subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/tags/autocomplete/`,
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('q')).toBe('inv');
      req.flush([]);
    });
  });

  // --- Correspondents ---

  describe('getCorrespondents', () => {
    it('sends GET to /correspondents/', () => {
      service.getCorrespondents().subscribe();
      const req = httpTesting.expectOne(`${API}/correspondents/`);
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('createCorrespondent', () => {
    it('sends POST to /correspondents/ with payload', () => {
      const data = { name: 'HMRC' };
      service.createCorrespondent(data).subscribe();
      const req = httpTesting.expectOne(`${API}/correspondents/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateCorrespondent', () => {
    it('sends PATCH to /correspondents/:id/ with payload', () => {
      const data = { name: 'Updated Corp' };
      service.updateCorrespondent(3, data).subscribe();
      const req = httpTesting.expectOne(`${API}/correspondents/3/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 3, ...data });
    });
  });

  describe('deleteCorrespondent', () => {
    it('sends DELETE to /correspondents/:id/', () => {
      service.deleteCorrespondent(3).subscribe();
      const req = httpTesting.expectOne(`${API}/correspondents/3/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('autocompleteCorrespondent', () => {
    it('sends GET to /correspondents/autocomplete/ with q param', () => {
      service.autocompleteCorrespondent('hm').subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/correspondents/autocomplete/`,
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('q')).toBe('hm');
      req.flush([]);
    });
  });

  // --- Cabinets ---

  describe('getCabinets', () => {
    it('sends GET to /cabinets/', () => {
      service.getCabinets().subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/`);
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('getCabinetTree', () => {
    it('sends GET to /cabinets/tree/', () => {
      service.getCabinetTree().subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/tree/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createCabinet', () => {
    it('sends POST to /cabinets/ with payload', () => {
      const data = { name: 'Finance' };
      service.createCabinet(data).subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateCabinet', () => {
    it('sends PATCH to /cabinets/:id/ with payload', () => {
      const data = { name: 'HR' };
      service.updateCabinet(2, data).subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/2/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 2, ...data });
    });
  });

  describe('deleteCabinet', () => {
    it('sends DELETE to /cabinets/:id/', () => {
      service.deleteCabinet(2).subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/2/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('moveCabinet', () => {
    it('sends POST to /cabinets/:id/move/ with parent id', () => {
      service.moveCabinet(2, 10).subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/2/move/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ parent: 10 });
      req.flush({ id: 2 });
    });

    it('sends null parent when moving to root', () => {
      service.moveCabinet(2, null).subscribe();
      const req = httpTesting.expectOne(`${API}/cabinets/2/move/`);
      expect(req.request.body).toEqual({ parent: null });
      req.flush({ id: 2 });
    });
  });

  describe('autocompleteCabinet', () => {
    it('sends GET to /cabinets/autocomplete/ with q param', () => {
      service.autocompleteCabinet('fin').subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/cabinets/autocomplete/`,
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('q')).toBe('fin');
      req.flush([]);
    });
  });

  // --- Storage Paths ---

  describe('getStoragePaths', () => {
    it('sends GET to /storage-paths/', () => {
      service.getStoragePaths().subscribe();
      const req = httpTesting.expectOne(`${API}/storage-paths/`);
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('createStoragePath', () => {
    it('sends POST to /storage-paths/ with payload', () => {
      const data = { name: '/docs/invoices' };
      service.createStoragePath(data).subscribe();
      const req = httpTesting.expectOne(`${API}/storage-paths/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateStoragePath', () => {
    it('sends PATCH to /storage-paths/:id/ with payload', () => {
      const data = { name: '/docs/updated' };
      service.updateStoragePath(7, data).subscribe();
      const req = httpTesting.expectOne(`${API}/storage-paths/7/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 7, ...data });
    });
  });

  describe('deleteStoragePath', () => {
    it('sends DELETE to /storage-paths/:id/', () => {
      service.deleteStoragePath(7).subscribe();
      const req = httpTesting.expectOne(`${API}/storage-paths/7/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('autocompleteStoragePath', () => {
    it('sends GET to /storage-paths/autocomplete/ with q param', () => {
      service.autocompleteStoragePath('doc').subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/storage-paths/autocomplete/`,
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('q')).toBe('doc');
      req.flush([]);
    });
  });

  // --- Custom Fields ---

  describe('getCustomFields', () => {
    it('sends GET to /custom-fields/', () => {
      service.getCustomFields().subscribe();
      const req = httpTesting.expectOne(`${API}/custom-fields/`);
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('getCustomField', () => {
    it('sends GET to /custom-fields/:id/', () => {
      service.getCustomField(4).subscribe();
      const req = httpTesting.expectOne(`${API}/custom-fields/4/`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 4 });
    });
  });

  describe('createCustomField', () => {
    it('sends POST to /custom-fields/ with payload', () => {
      const data = { name: 'Invoice Number', field_type: 'text' };
      service.createCustomField(data).subscribe();
      const req = httpTesting.expectOne(`${API}/custom-fields/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateCustomField', () => {
    it('sends PATCH to /custom-fields/:id/ with payload', () => {
      const data = { name: 'Updated Field' };
      service.updateCustomField(4, data).subscribe();
      const req = httpTesting.expectOne(`${API}/custom-fields/4/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 4, ...data });
    });
  });

  describe('deleteCustomField', () => {
    it('sends DELETE to /custom-fields/:id/', () => {
      service.deleteCustomField(4).subscribe();
      const req = httpTesting.expectOne(`${API}/custom-fields/4/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Custom Field Instances ---

  describe('getDocumentCustomFields', () => {
    it('sends GET to /documents/:docId/custom-fields/', () => {
      service.getDocumentCustomFields(10).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/10/custom-fields/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('setDocumentCustomField', () => {
    it('sends POST to /documents/:docId/custom-fields/ with correct body', () => {
      service.setDocumentCustomField(10, 4, 'INV-001').subscribe();
      const req = httpTesting.expectOne(`${API}/documents/10/custom-fields/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        document: 10,
        field: 4,
        value: 'INV-001',
      });
      req.flush({ id: 1 });
    });
  });

  describe('updateDocumentCustomField', () => {
    it('sends PATCH to /documents/:docId/custom-fields/:instanceId/ with value', () => {
      service.updateDocumentCustomField(10, 99, 'INV-002').subscribe();
      const req = httpTesting.expectOne(
        `${API}/documents/10/custom-fields/99/`,
      );
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ value: 'INV-002' });
      req.flush({ id: 99 });
    });
  });

  describe('deleteDocumentCustomField', () => {
    it('sends DELETE to /documents/:docId/custom-fields/:instanceId/', () => {
      service.deleteDocumentCustomField(10, 99).subscribe();
      const req = httpTesting.expectOne(
        `${API}/documents/10/custom-fields/99/`,
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Metadata Types ---

  describe('getMetadataTypes', () => {
    it('sends GET to /metadata-types/', () => {
      service.getMetadataTypes().subscribe();
      const req = httpTesting.expectOne(`${API}/metadata-types/`);
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });
  });

  describe('getMetadataType', () => {
    it('sends GET to /metadata-types/:id/', () => {
      service.getMetadataType(6).subscribe();
      const req = httpTesting.expectOne(`${API}/metadata-types/6/`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 6 });
    });
  });

  describe('createMetadataType', () => {
    it('sends POST to /metadata-types/ with payload', () => {
      const data = { name: 'Author' };
      service.createMetadataType(data).subscribe();
      const req = httpTesting.expectOne(`${API}/metadata-types/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateMetadataType', () => {
    it('sends PATCH to /metadata-types/:id/ with payload', () => {
      const data = { name: 'Revised Author' };
      service.updateMetadataType(6, data).subscribe();
      const req = httpTesting.expectOne(`${API}/metadata-types/6/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 6, ...data });
    });
  });

  describe('deleteMetadataType', () => {
    it('sends DELETE to /metadata-types/:id/', () => {
      service.deleteMetadataType(6).subscribe();
      const req = httpTesting.expectOne(`${API}/metadata-types/6/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('getMetadataTypeLookupOptions', () => {
    it('sends GET to /metadata-types/:id/lookup-options/', () => {
      service.getMetadataTypeLookupOptions(6).subscribe();
      const req = httpTesting.expectOne(
        `${API}/metadata-types/6/lookup-options/`,
      );
      expect(req.request.method).toBe('GET');
      req.flush({ options: ['Option A', 'Option B'] });
    });
  });

  // --- Document Metadata ---

  describe('getDocumentMetadata', () => {
    it('sends GET to /documents/:docId/metadata/', () => {
      service.getDocumentMetadata(10).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/10/metadata/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('setDocumentMetadata', () => {
    it('sends POST to /documents/:docId/metadata/ with correct body', () => {
      service.setDocumentMetadata(10, 6, 'John Doe').subscribe();
      const req = httpTesting.expectOne(`${API}/documents/10/metadata/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        document: 10,
        metadata_type: 6,
        value: 'John Doe',
      });
      req.flush({ id: 1 });
    });
  });

  describe('updateDocumentMetadata', () => {
    it('sends PATCH to /documents/:docId/metadata/:instanceId/ with value', () => {
      service.updateDocumentMetadata(10, 55, 'Jane Doe').subscribe();
      const req = httpTesting.expectOne(`${API}/documents/10/metadata/55/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ value: 'Jane Doe' });
      req.flush({ id: 55 });
    });
  });

  describe('deleteDocumentMetadata', () => {
    it('sends DELETE to /documents/:docId/metadata/:instanceId/', () => {
      service.deleteDocumentMetadata(10, 55).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/10/metadata/55/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Document Type Assignments ---

  describe('getDocTypeCustomFields', () => {
    it('sends GET to /document-types/:id/custom-fields/', () => {
      service.getDocTypeCustomFields(20).subscribe();
      const req = httpTesting.expectOne(
        `${API}/document-types/20/custom-fields/`,
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('assignDocTypeCustomField', () => {
    it('sends POST to /document-types/:id/custom-fields/ with correct body', () => {
      service.assignDocTypeCustomField(20, 4, true).subscribe();
      const req = httpTesting.expectOne(
        `${API}/document-types/20/custom-fields/`,
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        document_type: 20,
        custom_field: 4,
        required: true,
      });
      req.flush({ id: 1 });
    });
  });

  describe('removeDocTypeCustomField', () => {
    it('sends DELETE to /document-types/:id/custom-fields/:assignmentId/', () => {
      service.removeDocTypeCustomField(20, 88).subscribe();
      const req = httpTesting.expectOne(
        `${API}/document-types/20/custom-fields/88/`,
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('getDocTypeMetadata', () => {
    it('sends GET to /document-types/:id/metadata-types/', () => {
      service.getDocTypeMetadata(20).subscribe();
      const req = httpTesting.expectOne(
        `${API}/document-types/20/metadata-types/`,
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('assignDocTypeMetadata', () => {
    it('sends POST to /document-types/:id/metadata-types/ with correct body', () => {
      service.assignDocTypeMetadata(20, 6, false).subscribe();
      const req = httpTesting.expectOne(
        `${API}/document-types/20/metadata-types/`,
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        document_type: 20,
        metadata_type: 6,
        required: false,
      });
      req.flush({ id: 1 });
    });
  });

  describe('removeDocTypeMetadata', () => {
    it('sends DELETE to /document-types/:id/metadata-types/:assignmentId/', () => {
      service.removeDocTypeMetadata(20, 77).subscribe();
      const req = httpTesting.expectOne(
        `${API}/document-types/20/metadata-types/77/`,
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });
});
