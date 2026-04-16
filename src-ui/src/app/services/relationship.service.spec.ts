import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { RelationshipService } from './relationship.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

const mockRelType = {
  id: 1,
  slug: 'related-to',
  label: 'Related To',
  icon: 'link',
  is_directional: false,
  is_builtin: true,
};

const mockRelationship = {
  id: 10,
  source_document: 1,
  target_document: 2,
  source_title: 'Doc A',
  target_title: 'Doc B',
  relationship_type: 1,
  relationship_type_label: 'Related To',
  relationship_type_icon: 'link',
  notes: '',
  created_at: '2024-01-01T00:00:00Z',
};

describe('RelationshipService', () => {
  let service: RelationshipService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        RelationshipService,
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(RelationshipService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // --- Relationship Types ---

  describe('getRelationshipTypes', () => {
    it('should GET all relationship types', () => {
      service.getRelationshipTypes().subscribe((result) => {
        expect(result).toEqual([mockRelType]);
      });

      const req = httpMock.expectOne(`${API}/relationship-types/`);
      expect(req.request.method).toBe('GET');
      req.flush([mockRelType]);
    });
  });

  describe('createRelationshipType', () => {
    it('should POST a new relationship type', () => {
      const data = { slug: 'supersedes', label: 'Supersedes', icon: 'arrow-up' };
      const created = { id: 2, ...data, is_directional: true, is_builtin: false };

      service.createRelationshipType(data).subscribe((result) => {
        expect(result).toEqual(created);
      });

      const req = httpMock.expectOne(`${API}/relationship-types/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush(created);
    });
  });

  // --- Document Relationships ---

  describe('getDocumentRelationships', () => {
    it('should GET relationships for a document', () => {
      service.getDocumentRelationships(1).subscribe((result) => {
        expect(result).toEqual([mockRelationship]);
      });

      const req = httpMock.expectOne(`${API}/documents/1/relationships/`);
      expect(req.request.method).toBe('GET');
      req.flush([mockRelationship]);
    });
  });

  describe('createDocumentRelationship', () => {
    it('should POST to create a relationship on a document', () => {
      const data = { target_document: 2, relationship_type: 1 };

      service.createDocumentRelationship(1, data).subscribe((result) => {
        expect(result).toEqual(mockRelationship);
      });

      const req = httpMock.expectOne(`${API}/documents/1/relationships/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush(mockRelationship);
    });
  });

  describe('deleteDocumentRelationship', () => {
    it('should DELETE a specific relationship', () => {
      service.deleteDocumentRelationship(1, 10).subscribe();

      const req = httpMock.expectOne(`${API}/documents/1/relationships/10/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Relationship Graph ---

  describe('getRelationshipGraph', () => {
    it('should GET the relationship graph with default depth=1', () => {
      const mockGraph = {
        nodes: [
          { id: 1, title: 'Doc A', document_type: null },
          { id: 2, title: 'Doc B', document_type: 'Invoice' },
        ],
        edges: [{ source: 1, target: 2, type: 'related-to', label: 'Related To' }],
      };

      service.getRelationshipGraph(1).subscribe((result) => {
        expect(result).toEqual(mockGraph);
      });

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/documents/1/relationship-graph/` &&
          r.params.get('depth') === '1',
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockGraph);
    });

    it('should GET the relationship graph with a custom depth', () => {
      service.getRelationshipGraph(5, 3).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/documents/5/relationship-graph/` &&
          r.params.get('depth') === '3',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ nodes: [], edges: [] });
    });
  });
});
