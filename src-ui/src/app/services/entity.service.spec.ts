import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { EntityService } from './entity.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

describe('EntityService', () => {
  let service: EntityService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        EntityService,
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(EntityService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getEntityTypes', () => {
    it('should GET all entity types', () => {
      const mockPage = {
        count: 1,
        results: [
          {
            id: 1,
            name: 'person',
            label: 'Person',
            color: '#ff0000',
            icon: 'person',
            enabled: true,
          },
        ],
      };

      service.getEntityTypes().subscribe((result) => {
        expect(result).toEqual(mockPage);
      });

      const req = httpMock.expectOne(`${API}/entity-types/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockPage);
    });
  });

  describe('getEntities', () => {
    it('maps the backend aggregate entity type name for document and co-occurrence drilldown', () => {
      service.getEntities().subscribe((response) => expect(response.results[0].entity_type).toBe('PERSON'));
      const request = httpMock.expectOne((request) => request.url === `${API}/entities/`);
      expect(request.request.params.get('aggregate')).toBe('true');
      request.flush([{ value: 'Alice Johnson', entity_type_name: 'PERSON', entity_type_color: '#f00', document_count: 1 }]);
    });
    it('should GET entities without params', () => {
      const entity = { value: 'Alice', entity_type_name: 'PERSON', document_count: 3 };

      service.getEntities().subscribe((result) => {
        expect(result).toEqual({ count: 1, next: null, previous: null, results: [{ ...entity, entity_type: 'PERSON' }] });
      });

      const req = httpMock.expectOne((request) => request.url === `${API}/entities/`);
      expect(req.request.method).toBe('GET');
      req.flush([entity]);
    });

    it('should pass entity_type and search params', () => {
      service.getEntities({ entity_type: 'person', search: 'Alice' }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/entities/` &&
          r.params.get('entity_type') === 'person' &&
          r.params.get('value') === 'Alice',
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('paginates the bare aggregate response without requesting unsupported server pagination', () => {
      service.getEntities({ page: 2, page_size: 1 }).subscribe((response) => {
        expect(response.count).toBe(2);
        expect(response.results.map((entity) => entity.value)).toEqual(['Bob']);
      });

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/entities/` &&
          !r.params.has('page') &&
          !r.params.has('page_size'),
      );
      expect(req.request.method).toBe('GET');
      req.flush([
        { value: 'Alice', entity_type_name: 'PERSON', document_count: 3 },
        { value: 'Bob', entity_type_name: 'PERSON', document_count: 1 },
      ]);
    });

    it('should omit undefined and empty string params', () => {
      service.getEntities({ entity_type: '', search: undefined }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/entities/` &&
          !r.params.has('entity_type') &&
          !r.params.has('value'),
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getDocumentEntities', () => {
    it('should GET entities for a document', () => {
      const mockEntities = [
        {
          id: 1,
          document: 7,
          entity_type: 2,
          entity_type_name: 'Person',
          entity_type_color: '#00f',
          value: 'Bob',
          raw_value: 'Bob Smith',
          confidence: 0.95,
          start_offset: 10,
          end_offset: 13,
          page_number: 1,
        },
      ];

      service.getDocumentEntities(7).subscribe((result) => {
        expect(result).toEqual(mockEntities);
      });

      const req = httpMock.expectOne(`${API}/documents/7/entities/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockEntities);
    });
  });

  describe('getEntityDocuments', () => {
    it('should GET documents for an entity value', () => {
      const docs = [{ document_id: 3, title: 'Report' }];

      service.getEntityDocuments('person', 'Alice').subscribe((result) => {
        expect(result).toEqual(docs);
      });

      const req = httpMock.expectOne(`${API}/entities/person/Alice/documents/`);
      expect(req.request.method).toBe('GET');
      req.flush([{ id: 3, title: 'Report' }]);
    });

    it('should URL-encode special characters in the entity value', () => {
      service.getEntityDocuments('org', 'AT&T Inc.').subscribe();

      const req = httpMock.expectOne(
        `${API}/entities/org/${encodeURIComponent('AT&T Inc.')}/documents/`,
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getCooccurrence', () => {
    it('should GET cooccurrence data for an entity', () => {
      const mockData = [
        {
          entity: { value: 'Bob', entity_type: 'person', document_count: 2 },
          count: 5,
        },
      ];

      service.getCooccurrence('person', 'Alice').subscribe((result) => {
        expect(result).toEqual(mockData);
      });

      const req = httpMock.expectOne(`${API}/entities/person/Alice/cooccurrence/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockData);
    });
  });
});
