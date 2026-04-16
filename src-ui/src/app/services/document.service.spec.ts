import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { HttpTestingController } from '@angular/common/http/testing';

import { DocumentService } from './document.service';
import {
  Document,
  DocumentType,
  DocumentVersion,
  PaginatedResponse,
} from '../models/document.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;
const DOCS_URL = `${API}/documents`;
const TYPES_URL = `${API}/document-types`;

// Minimal fixture factories
function makeDocument(overrides: Partial<Document> = {}): Document {
  return {
    id: 1,
    uuid: 'uuid-1',
    title: 'Test Doc',
    content: 'Some content',
    document_type: null,
    document_type_name: null,
    correspondent: null,
    correspondent_name: null,
    cabinet: null,
    cabinet_name: null,
    storage_path: null,
    tag_ids: [],
    original_filename: 'test.pdf',
    mime_type: 'application/pdf',
    checksum: 'abc',
    archive_checksum: '',
    page_count: 1,
    filename: null,
    archive_filename: null,
    thumbnail_path: '/thumb/1',
    created: '2024-01-01',
    added: '2024-01-01',
    archive_serial_number: null,
    language: 'en',
    owner: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makePaginated<T>(results: T[]): PaginatedResponse<T> {
  return { count: results.length, next: null, previous: null, results };
}

function makeDocumentType(overrides: Partial<DocumentType> = {}): DocumentType {
  return {
    id: 1,
    name: 'Invoice',
    slug: 'invoice',
    trash_time_period: null,
    trash_time_unit: null,
    delete_time_period: null,
    delete_time_unit: null,
    match: '',
    matching_algorithm: 0,
    is_insensitive: false,
    document_count: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeVersion(overrides: Partial<DocumentVersion> = {}): DocumentVersion {
  return {
    id: 1,
    version_number: 1,
    comment: '',
    is_active: true,
    file: null,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('DocumentService', () => {
  let service: DocumentService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DocumentService,
      ],
    });
    service = TestBed.inject(DocumentService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // --- getDocuments() ---

  describe('getDocuments()', () => {
    it('should GET /documents/ with no params', () => {
      const mockResp = makePaginated([makeDocument()]);
      service.getDocuments().subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne((r) => r.url === `${DOCS_URL}/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResp);
    });

    it('should pass query params correctly', () => {
      service
        .getDocuments({ page: 2, page_size: 10, search: 'invoice' })
        .subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${DOCS_URL}/` &&
          r.params.get('page') === '2' &&
          r.params.get('page_size') === '10' &&
          r.params.get('search') === 'invoice',
      );
      expect(req.request.method).toBe('GET');
      req.flush(makePaginated([]));
    });

    it('should omit undefined/null/empty params', () => {
      service.getDocuments({ page: 1, search: '' }).subscribe();

      const req = httpMock.expectOne((r) => r.url === `${DOCS_URL}/`);
      expect(req.request.params.has('search')).toBe(false);
      expect(req.request.params.get('page')).toBe('1');
      req.flush(makePaginated([]));
    });
  });

  // --- getDocument() ---

  describe('getDocument()', () => {
    it('should GET /documents/:id/', () => {
      const doc = makeDocument({ id: 42 });
      service.getDocument(42).subscribe((res) => expect(res).toEqual(doc));

      const req = httpMock.expectOne(`${DOCS_URL}/42/`);
      expect(req.request.method).toBe('GET');
      req.flush(doc);
    });

    it('should propagate 404 errors', () => {
      let err: unknown;
      service.getDocument(999).subscribe({ error: (e) => (err = e) });
      httpMock
        .expectOne(`${DOCS_URL}/999/`)
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(err).toBeTruthy();
    });
  });

  // --- createDocument() ---

  describe('createDocument()', () => {
    it('should POST to /documents/', () => {
      const payload: Partial<Document> = { title: 'New Doc' };
      const created = makeDocument({ title: 'New Doc' });

      service.createDocument(payload).subscribe((res) => expect(res).toEqual(created));

      const req = httpMock.expectOne(`${DOCS_URL}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(created);
    });
  });

  // --- updateDocument() ---

  describe('updateDocument()', () => {
    it('should PATCH /documents/:id/', () => {
      const payload: Partial<Document> = { title: 'Updated' };
      const updated = makeDocument({ id: 5, title: 'Updated' });

      service.updateDocument(5, payload).subscribe((res) => expect(res).toEqual(updated));

      const req = httpMock.expectOne(`${DOCS_URL}/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(payload);
      req.flush(updated);
    });
  });

  // --- deleteDocument() ---

  describe('deleteDocument()', () => {
    it('should DELETE /documents/:id/', () => {
      service.deleteDocument(3).subscribe();

      const req = httpMock.expectOne(`${DOCS_URL}/3/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- restoreDocument() ---

  describe('restoreDocument()', () => {
    it('should POST to /documents/:id/restore/', () => {
      const restored = makeDocument({ id: 7 });
      service.restoreDocument(7).subscribe((res) => expect(res).toEqual(restored));

      const req = httpMock.expectOne(`${DOCS_URL}/7/restore/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(restored);
    });
  });

  // --- getDeletedDocuments() ---

  describe('getDeletedDocuments()', () => {
    it('should GET /documents/deleted/', () => {
      const mockResp = makePaginated([makeDocument()]);
      service.getDeletedDocuments().subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne(`${DOCS_URL}/deleted/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResp);
    });
  });

  // --- getPreviewUrl() / getDownloadUrl() ---

  describe('getPreviewUrl()', () => {
    it('should return the correct preview URL string', () => {
      expect(service.getPreviewUrl(10)).toBe(`${DOCS_URL}/10/preview/`);
    });
  });

  describe('getDownloadUrl()', () => {
    it('should default to original version', () => {
      expect(service.getDownloadUrl(10)).toBe(`${DOCS_URL}/10/download/?version=original`);
    });

    it('should return archive version URL when specified', () => {
      expect(service.getDownloadUrl(10, 'archive')).toBe(
        `${DOCS_URL}/10/download/?version=archive`,
      );
    });
  });

  // --- getVersions() ---

  describe('getVersions()', () => {
    it('should GET /documents/:id/versions/', () => {
      const versions = [makeVersion(), makeVersion({ id: 2, version_number: 2, is_active: false })];
      service.getVersions(1).subscribe((res) => expect(res).toEqual(versions));

      const req = httpMock.expectOne(`${DOCS_URL}/1/versions/`);
      expect(req.request.method).toBe('GET');
      req.flush(versions);
    });
  });

  // --- activateVersion() ---

  describe('activateVersion()', () => {
    it('should POST to /documents/:docId/versions/:verId/activate/', () => {
      const activated = makeVersion({ id: 2, is_active: true });
      service.activateVersion(1, 2).subscribe((res) => expect(res).toEqual(activated));

      const req = httpMock.expectOne(`${DOCS_URL}/1/versions/2/activate/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(activated);
    });
  });

  // --- uploadNewVersion() ---

  describe('uploadNewVersion()', () => {
    it('should POST FormData to /documents/:id/files/', () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const mockVersion = makeVersion({ id: 3, version_number: 2 });

      service.uploadNewVersion(1, file, 'v2 upload').subscribe((res) => {
        expect(res).toEqual(mockVersion);
      });

      const req = httpMock.expectOne(`${DOCS_URL}/1/files/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toBeInstanceOf(FormData);
      const body = req.request.body as FormData;
      expect(body.get('document')).toBe(file);
      expect(body.get('comment')).toBe('v2 upload');
      req.flush(mockVersion);
    });

    it('should not append comment to FormData when comment is empty', () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      service.uploadNewVersion(1, file).subscribe();

      const req = httpMock.expectOne(`${DOCS_URL}/1/files/`);
      const body = req.request.body as FormData;
      expect(body.get('comment')).toBeNull();
      req.flush(makeVersion());
    });
  });

  // --- Document Types ---

  describe('getDocumentTypes()', () => {
    it('should GET /document-types/', () => {
      const mockResp = makePaginated([makeDocumentType()]);
      service.getDocumentTypes().subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne(`${TYPES_URL}/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResp);
    });
  });

  describe('getDocumentType()', () => {
    it('should GET /document-types/:id/', () => {
      const dt = makeDocumentType({ id: 5 });
      service.getDocumentType(5).subscribe((res) => expect(res).toEqual(dt));

      const req = httpMock.expectOne(`${TYPES_URL}/5/`);
      expect(req.request.method).toBe('GET');
      req.flush(dt);
    });
  });

  describe('createDocumentType()', () => {
    it('should POST to /document-types/', () => {
      const payload: Partial<DocumentType> = { name: 'Contract' };
      const created = makeDocumentType({ name: 'Contract' });

      service.createDocumentType(payload).subscribe((res) => expect(res).toEqual(created));

      const req = httpMock.expectOne(`${TYPES_URL}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(created);
    });
  });

  describe('updateDocumentType()', () => {
    it('should PATCH /document-types/:id/', () => {
      const payload: Partial<DocumentType> = { name: 'Receipt' };
      const updated = makeDocumentType({ id: 3, name: 'Receipt' });

      service.updateDocumentType(3, payload).subscribe((res) => expect(res).toEqual(updated));

      const req = httpMock.expectOne(`${TYPES_URL}/3/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(payload);
      req.flush(updated);
    });
  });

  describe('deleteDocumentType()', () => {
    it('should DELETE /document-types/:id/', () => {
      service.deleteDocumentType(4).subscribe();

      const req = httpMock.expectOne(`${TYPES_URL}/4/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- bulkOperation() ---

  describe('bulkOperation()', () => {
    it('should POST to /bulk/ with action and document_ids', () => {
      const payload = { action: 'delete', document_ids: [1, 2, 3] };
      const mockResp = { affected: 3 };

      service.bulkOperation(payload).subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne(`${API}/bulk/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(mockResp);
    });

    it('should include optional tag_ids and correspondent_id in bulk payload', () => {
      const payload = {
        action: 'modify',
        document_ids: [10, 20],
        tag_ids: [5, 6],
        correspondent_id: 7,
      };

      service.bulkOperation(payload).subscribe();

      const req = httpMock.expectOne(`${API}/bulk/`);
      expect(req.request.body).toEqual(payload);
      req.flush({ affected: 2 });
    });
  });
});
