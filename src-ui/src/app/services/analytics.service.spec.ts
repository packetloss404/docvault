import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AnalyticsService } from './analytics.service';
import { environment } from '../../environments/environment';

const BASE = environment.apiUrl;

describe('AnalyticsService', () => {
  let service: AnalyticsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AnalyticsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // --- Analytics ---

  describe('getAnalytics', () => {
    it('sends GET to /search/analytics/ with default days=30', () => {
      service.getAnalytics().subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/search/analytics/` &&
          r.params.get('days') === '30',
      );
      expect(req.request.method).toBe('GET');
      req.flush({
        top_queries: [],
        zero_result_queries: [],
        total_searches: 0,
        avg_click_position: 0,
        click_through_rate: 0,
      });
    });

    it('sends GET with custom days parameter', () => {
      service.getAnalytics(7).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/search/analytics/` &&
          r.params.get('days') === '7',
      );
      expect(req.request.method).toBe('GET');
      req.flush({
        top_queries: [],
        zero_result_queries: [],
        total_searches: 0,
        avg_click_position: 0,
        click_through_rate: 0,
      });
    });
  });

  describe('trackClick', () => {
    it('sends POST to /search/click/ with correct body', () => {
      const payload = { query: 'test', document_id: 42, position: 1 };
      service.trackClick(payload).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/click/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(null);
    });
  });

  describe('trackQuery', () => {
    it('sends POST to /search/query-log/ with correct body', () => {
      const payload = { query: 'hello', response_time_ms: 120, result_count: 5 };
      service.trackQuery(payload).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/query-log/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(null);
    });
  });

  // --- Synonyms ---

  describe('getSynonyms', () => {
    it('sends GET to /search/synonyms/', () => {
      service.getSynonyms().subscribe();
      const req = httpMock.expectOne(`${BASE}/search/synonyms/`);
      expect(req.request.method).toBe('GET');
      req.flush({ count: 0, results: [] });
    });
  });

  describe('createSynonym', () => {
    it('sends POST to /search/synonyms/ with body', () => {
      const data = { terms: ['foo', 'bar'], enabled: true };
      service.createSynonym(data).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/synonyms/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateSynonym', () => {
    it('sends PATCH to /search/synonyms/:id/ with body', () => {
      const data = { enabled: false };
      service.updateSynonym(5, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/synonyms/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 5, terms: [], enabled: false });
    });
  });

  describe('deleteSynonym', () => {
    it('sends DELETE to /search/synonyms/:id/', () => {
      service.deleteSynonym(3).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/synonyms/3/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Curations ---

  describe('getCurations', () => {
    it('sends GET to /search/curations/', () => {
      service.getCurations().subscribe();
      const req = httpMock.expectOne(`${BASE}/search/curations/`);
      expect(req.request.method).toBe('GET');
      req.flush({ count: 0, results: [] });
    });
  });

  describe('createCuration', () => {
    it('sends POST to /search/curations/ with body', () => {
      const data = { query_text: 'invoice', pinned_documents: [1, 2], hidden_documents: [], enabled: true };
      service.createCuration(data).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/curations/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 10, ...data });
    });
  });

  describe('updateCuration', () => {
    it('sends PATCH to /search/curations/:id/ with body', () => {
      const data = { enabled: false };
      service.updateCuration(10, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/curations/10/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 10, query_text: 'invoice', pinned_documents: [], hidden_documents: [], enabled: false });
    });
  });

  describe('deleteCuration', () => {
    it('sends DELETE to /search/curations/:id/', () => {
      service.deleteCuration(10).subscribe();
      const req = httpMock.expectOne(`${BASE}/search/curations/10/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });
});
