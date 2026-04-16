import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { SearchService } from './search.service';
import { AnalyticsService } from './analytics.service';
import {
  AutocompleteResult,
  SavedView,
  SavedViewListItem,
  SearchResponse,
} from '../models/search.model';
import { PaginatedResponse } from '../models/document.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

// Fixture factories
function makeSearchResponse(overrides: Partial<SearchResponse> = {}): SearchResponse {
  return {
    count: 0,
    page: 1,
    page_size: 25,
    results: [],
    facets: {},
    ...overrides,
  };
}

function makeAutocompleteResult(overrides: Partial<AutocompleteResult> = {}): AutocompleteResult {
  return {
    id: 1,
    title: 'Sample',
    correspondent: null,
    document_type: null,
    score: 0.9,
    ...overrides,
  };
}

function makeSavedView(overrides: Partial<SavedView> = {}): SavedView {
  return {
    id: 1,
    name: 'My View',
    display_mode: 'table',
    display_fields: ['title', 'created'],
    sort_field: 'created',
    sort_reverse: true,
    page_size: 25,
    show_on_dashboard: false,
    show_in_sidebar: true,
    filter_rules: [],
    owner: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeSavedViewListItem(overrides: Partial<SavedViewListItem> = {}): SavedViewListItem {
  return {
    id: 1,
    name: 'My View',
    display_mode: 'table',
    show_on_dashboard: false,
    show_in_sidebar: true,
    rule_count: 0,
    owner: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makePaginated<T>(results: T[]): PaginatedResponse<T> {
  return { count: results.length, next: null, previous: null, results };
}

// Mock AnalyticsService so search() tap() doesn't fire real HTTP POST calls
const mockAnalyticsService = {
  trackQuery: vi.fn(() => of(undefined)),
};

describe('SearchService', () => {
  let service: SearchService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        SearchService,
        { provide: AnalyticsService, useValue: mockAnalyticsService },
      ],
    });
    service = TestBed.inject(SearchService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // --- search() ---

  describe('search()', () => {
    it('should GET /search/ with no params when called with empty object', () => {
      const mockResp = makeSearchResponse();
      service.search({}).subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne((r) => r.url === `${API}/search/`);
      expect(req.request.method).toBe('GET');
      // No params should be set for empty input
      expect(req.request.params.keys().length).toBe(0);
      req.flush(mockResp);
    });

    it('should pass query param when provided', () => {
      service.search({ query: 'invoice' }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.url === `${API}/search/` && r.params.get('query') === 'invoice',
      );
      expect(req.request.method).toBe('GET');
      req.flush(makeSearchResponse());
    });

    it('should pass pagination params', () => {
      service.search({ query: 'receipt', page: 3, page_size: 20 }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/search/` &&
          r.params.get('query') === 'receipt' &&
          r.params.get('page') === '3' &&
          r.params.get('page_size') === '20',
      );
      req.flush(makeSearchResponse());
    });

    it('should pass document_type_id and correspondent_id', () => {
      service
        .search({ query: 'doc', document_type_id: 2, correspondent_id: 5 })
        .subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/search/` &&
          r.params.get('document_type_id') === '2' &&
          r.params.get('correspondent_id') === '5',
      );
      req.flush(makeSearchResponse());
    });

    it('should join tag_ids as a comma-separated string', () => {
      service.search({ tag_ids: [1, 2, 3] }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.url === `${API}/search/` && r.params.get('tag_ids') === '1,2,3',
      );
      req.flush(makeSearchResponse());
    });

    it('should pass date range params', () => {
      service
        .search({ created_after: '2024-01-01', created_before: '2024-12-31' })
        .subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/search/` &&
          r.params.get('created_after') === '2024-01-01' &&
          r.params.get('created_before') === '2024-12-31',
      );
      req.flush(makeSearchResponse());
    });

    it('should not include tag_ids param when array is empty', () => {
      service.search({ query: 'test', tag_ids: [] }).subscribe();

      const req = httpMock.expectOne((r) => r.url === `${API}/search/`);
      expect(req.request.params.has('tag_ids')).toBe(false);
      req.flush(makeSearchResponse());
    });

    it('should propagate HTTP errors from search', () => {
      let caughtError: unknown;
      service.search({ query: 'fail' }).subscribe({ error: (err) => (caughtError = err) });
      httpMock
        .expectOne((r) => r.url === `${API}/search/`)
        .flush({ detail: 'Server Error' }, { status: 500, statusText: 'Internal Server Error' });
      expect(caughtError).toBeTruthy();
    });
  });

  // --- autocomplete() ---

  describe('autocomplete()', () => {
    it('should GET /search/autocomplete/ with query param', () => {
      const mockResults = [makeAutocompleteResult(), makeAutocompleteResult({ id: 2, title: 'Other' })];

      service.autocomplete('inv').subscribe((res) => expect(res).toEqual(mockResults));

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/search/autocomplete/` && r.params.get('query') === 'inv',
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResults);
    });

    it('should return an empty array when no matches', () => {
      service.autocomplete('zzz').subscribe((res) => expect(res).toEqual([]));

      httpMock
        .expectOne((r) => r.url === `${API}/search/autocomplete/`)
        .flush([]);
    });
  });

  // --- similarDocuments() ---

  describe('similarDocuments()', () => {
    it('should GET /ai/similar/ with document_id param', () => {
      const mockResults = { count: 1, results: [{ id: 5, title: 'Similar Doc' }] };

      service.similarDocuments(42).subscribe((res) => expect(res).toEqual(mockResults));

      const req = httpMock.expectOne(
        (r) => r.url === `${API}/ai/similar/` && r.params.get('document_id') === '42',
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResults);
    });

    it('should propagate HTTP errors from similarDocuments', () => {
      let err: unknown;
      service.similarDocuments(9999).subscribe({ error: (e) => (err = e) });
      httpMock
        .expectOne((r) => r.url === `${API}/ai/similar/` && r.params.get('document_id') === '9999')
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(err).toBeTruthy();
    });
  });

  // --- getSavedViews() ---

  describe('getSavedViews()', () => {
    it('should GET /saved-views/', () => {
      const mockResp = makePaginated([makeSavedViewListItem()]);
      service.getSavedViews().subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne(`${API}/saved-views/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResp);
    });
  });

  // --- getSavedView() ---

  describe('getSavedView()', () => {
    it('should GET /saved-views/:id/', () => {
      const view = makeSavedView({ id: 3 });
      service.getSavedView(3).subscribe((res) => expect(res).toEqual(view));

      const req = httpMock.expectOne(`${API}/saved-views/3/`);
      expect(req.request.method).toBe('GET');
      req.flush(view);
    });
  });

  // --- createSavedView() ---

  describe('createSavedView()', () => {
    it('should POST to /saved-views/', () => {
      const payload: Partial<SavedView> = { name: 'New View', display_mode: 'table' };
      const created = makeSavedView({ name: 'New View' });

      service.createSavedView(payload).subscribe((res) => expect(res).toEqual(created));

      const req = httpMock.expectOne(`${API}/saved-views/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(created);
    });
  });

  // --- updateSavedView() ---

  describe('updateSavedView()', () => {
    it('should PATCH /saved-views/:id/', () => {
      const payload: Partial<SavedView> = { name: 'Renamed View' };
      const updated = makeSavedView({ id: 4, name: 'Renamed View' });

      service.updateSavedView(4, payload).subscribe((res) => expect(res).toEqual(updated));

      const req = httpMock.expectOne(`${API}/saved-views/4/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(payload);
      req.flush(updated);
    });
  });

  // --- deleteSavedView() ---

  describe('deleteSavedView()', () => {
    it('should DELETE /saved-views/:id/', () => {
      service.deleteSavedView(5).subscribe();

      const req = httpMock.expectOne(`${API}/saved-views/5/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- executeSavedView() ---

  describe('executeSavedView()', () => {
    it('should GET /saved-views/:id/execute/ without page param by default', () => {
      const mockResp = makePaginated([]);
      service.executeSavedView(2).subscribe((res) => expect(res).toEqual(mockResp));

      const req = httpMock.expectOne((r) => r.url === `${API}/saved-views/2/execute/`);
      expect(req.request.method).toBe('GET');
      expect(req.request.params.has('page')).toBe(false);
      req.flush(mockResp);
    });

    it('should include page param when provided', () => {
      service.executeSavedView(2, 3).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API}/saved-views/2/execute/` && r.params.get('page') === '3',
      );
      req.flush(makePaginated([]));
    });
  });

  // --- getDashboardViews() ---

  describe('getDashboardViews()', () => {
    it('should GET /saved-views/dashboard/', () => {
      const views = [makeSavedViewListItem({ show_on_dashboard: true })];
      service.getDashboardViews().subscribe((res) => expect(res).toEqual(views));

      const req = httpMock.expectOne(`${API}/saved-views/dashboard/`);
      expect(req.request.method).toBe('GET');
      req.flush(views);
    });
  });

  // --- getSidebarViews() ---

  describe('getSidebarViews()', () => {
    it('should GET /saved-views/sidebar/', () => {
      const views = [makeSavedViewListItem({ show_in_sidebar: true })];
      service.getSidebarViews().subscribe((res) => expect(res).toEqual(views));

      const req = httpMock.expectOne(`${API}/saved-views/sidebar/`);
      expect(req.request.method).toBe('GET');
      req.flush(views);
    });
  });
});
