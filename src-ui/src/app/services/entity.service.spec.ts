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
    it('should GET entities without params', () => {
      const mockPage = {
        count: 2,
        results: [
          { value: 'Alice', entity_type: 'person', document_count: 3 },
        ],
      };

      service.getEntities().subscribe((result) => {
        expect(result).toEqual(mockPage);
      });

      const req = httpMock.expectOne(`${API}/entities/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockPage);
    });

    it('should pass entity_type and search params', () => {
      service.getEntities({ entity_type: 'person', search: 'Alice' }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/entities/` &&
          r.params.get('entity_type') === 'person' &&
          r.params.get('search') === 'Alice',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ count: 0, results: [] });
    });

    it('should pass page and page_size params', () => {
      service.getEntities({ page: 2, page_size: 20 }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/entities/` &&
          r.params.get('page') === '2' &&
          r.params.get('page_size') === '20',
      );
      expect(req.request.method).toBe('GET');
      req.flush({ count: 0, results: [] });
    });

    it('should omit undefined and empty string params', () => {
      service.getEntities({ entity_type: '', search: undefined }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/entities/` &&
          !r.params.has('entity_type') &&
          !r.params.has('search'),
      );
      expect(req.request.method).toBe('GET');
      req.flush({ count: 0, results: [] });
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
      req.flush(docs);
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

      service.getCooccurrence(1).subscribe((result) => {
        expect(result).toEqual(mockData);
      });

      const req = httpMock.expectOne(`${API}/entities/1/cooccurrence/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockData);
    });
  });
});
