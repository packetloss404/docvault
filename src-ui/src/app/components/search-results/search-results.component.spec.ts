import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { ActivatedRoute, Router } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { vi } from 'vitest';
import { SearchResultsComponent } from './search-results.component';
import { SearchService } from '../../services/search.service';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchResponse, SearchResult, SearchFacets } from '../../models/search.model';
import { FilterRow } from '../search-filter-builder/search-filter-builder.component';

const makeResult = (overrides: Partial<SearchResult> = {}): SearchResult => ({
  id: 1,
  title: 'Test Doc',
  content: 'Some content',
  correspondent: null,
  document_type: null,
  tags: [],
  created: '2024-01-01',
  score: 0.9,
  ...overrides,
});

const makeResponse = (overrides: Partial<SearchResponse> = {}): SearchResponse => ({
  count: 0,
  page: 1,
  page_size: 25,
  results: [],
  facets: {},
  ...overrides,
});

describe('SearchResultsComponent', () => {
  let component: SearchResultsComponent;
  let fixture: ComponentFixture<SearchResultsComponent>;
  let searchService: { search: ReturnType<typeof vi.fn> };
  let analyticsService: { trackClick: ReturnType<typeof vi.fn> };
  let queryParamsSubject: Subject<Record<string, string>>;
  let router: Router;

  beforeEach(async () => {
    queryParamsSubject = new Subject<Record<string, string>>();

    searchService = { search: vi.fn().mockReturnValue(of(makeResponse())) };
    analyticsService = { trackClick: vi.fn().mockReturnValue(of(undefined)) };

    await TestBed.configureTestingModule({
      imports: [SearchResultsComponent],
      providers: [
        provideRouter([]),
        { provide: SearchService, useValue: searchService },
        { provide: AnalyticsService, useValue: analyticsService },
        {
          provide: ActivatedRoute,
          useValue: { queryParams: queryParamsSubject.asObservable() },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SearchResultsComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit / queryParams subscription', () => {
    it('does not call search when query param is empty', () => {
      searchService.search.mockClear();
      queryParamsSubject.next({ q: '' });
      expect(searchService.search).not.toHaveBeenCalled();
    });

    it('sets query and page from route params, then calls doSearch when q is present', () => {
      searchService.search.mockReturnValue(of(makeResponse({ count: 3, results: [makeResult()] })));
      queryParamsSubject.next({ q: 'invoice', page: '2' });

      expect(component.query()).toBe('invoice');
      expect(component.currentPage()).toBe(2);
      expect(searchService.search).toHaveBeenCalledWith(
        expect.objectContaining({ query: 'invoice', page: 2 }),
      );
    });

    it('defaults page to 1 when not provided in params', () => {
      queryParamsSubject.next({ q: 'hello' });
      expect(component.currentPage()).toBe(1);
    });
  });

  describe('doSearch', () => {
    it('sets loading to true while search is in progress', () => {
      const slowSubject = new Subject<SearchResponse>();
      searchService.search.mockReturnValue(slowSubject.asObservable());

      component.query.set('test');
      component.doSearch();

      expect(component.loading()).toBe(true);
    });

    it('populates results, facets and totalCount on success', () => {
      const result = makeResult({ id: 42, title: 'Invoice 2024' });
      const facets: SearchFacets = { tags: [{ key: 'finance', count: 5 }] };
      searchService.search.mockReturnValue(
        of(makeResponse({ count: 1, results: [result], facets })),
      );

      component.query.set('invoice');
      component.doSearch();

      expect(component.results()).toEqual([result]);
      expect(component.facets()).toEqual(facets);
      expect(component.totalCount()).toBe(1);
      expect(component.loading()).toBe(false);
    });

    it('sets loading to false on error', () => {
      searchService.search.mockReturnValue(throwError(() => new Error('Network error')));

      component.query.set('test');
      component.doSearch();

      expect(component.loading()).toBe(false);
    });

    it('passes current page and page size to service', () => {
      component.query.set('report');
      component.currentPage.set(3);
      component.pageSize.set(10);
      component.doSearch();

      expect(searchService.search).toHaveBeenCalledWith(
        expect.objectContaining({ query: 'report', page: 3, page_size: 10 }),
      );
    });
  });

  describe('trackResultClick', () => {
    it('calls analyticsService.trackClick with query, document id and position', () => {
      component.query.set('contract');
      const result = makeResult({ id: 7 });

      component.trackResultClick(result, 3);

      expect(analyticsService.trackClick).toHaveBeenCalledWith({
        query: 'contract',
        document_id: 7,
        position: 3,
      });
    });

    it('subscribes to the returned observable', () => {
      component.query.set('q');
      const mockSub = vi.fn();
      analyticsService.trackClick.mockReturnValue({ subscribe: mockSub });

      component.trackResultClick(makeResult(), 1);

      expect(mockSub).toHaveBeenCalled();
    });
  });

  describe('onFiltersChange', () => {
    it('updates activeFilters signal', () => {
      const filters: FilterRow[] = [{ field: 'title', operator: 'contains', value: 'foo' }];
      component.onFiltersChange(filters);
      expect(component.activeFilters()).toEqual(filters);
    });

    it('resets currentPage to 1', () => {
      component.currentPage.set(5);
      component.onFiltersChange([]);
      expect(component.currentPage()).toBe(1);
    });

    it('calls doSearch if query is non-empty', () => {
      searchService.search.mockReturnValue(of(makeResponse()));
      component.query.set('test');
      const callsBefore = (searchService.search as ReturnType<typeof vi.fn>).mock.calls.length;

      component.onFiltersChange([{ field: 'title', operator: 'contains', value: 'x' }]);

      expect((searchService.search as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(callsBefore);
    });

    it('does not call doSearch when query is empty', () => {
      component.query.set('');
      searchService.search.mockClear();

      component.onFiltersChange([{ field: 'title', operator: 'contains', value: 'x' }]);

      expect(searchService.search).not.toHaveBeenCalled();
    });
  });

  describe('totalPages', () => {
    it('returns ceil(totalCount / pageSize)', () => {
      component.totalCount.set(55);
      component.pageSize.set(25);
      expect(component.totalPages()).toBe(3);
    });

    it('returns 0 when totalCount is 0', () => {
      component.totalCount.set(0);
      expect(component.totalPages()).toBe(0);
    });
  });

  describe('onSearch', () => {
    it('resets currentPage to 1 and navigates with query params', () => {
      const navigateSpy = vi.spyOn(router, 'navigate');
      component.currentPage.set(4);
      component.query.set('hello');

      component.onSearch();

      expect(component.currentPage()).toBe(1);
      expect(navigateSpy).toHaveBeenCalledWith(
        ['/search'],
        { queryParams: { q: 'hello', page: 1 } },
      );
    });
  });

  describe('goToPage', () => {
    it('sets currentPage and navigates', () => {
      const navigateSpy = vi.spyOn(router, 'navigate');
      component.query.set('docs');

      component.goToPage(3);

      expect(component.currentPage()).toBe(3);
      expect(navigateSpy).toHaveBeenCalledWith(
        ['/search'],
        { queryParams: { q: 'docs', page: 3 } },
      );
    });
  });
});
