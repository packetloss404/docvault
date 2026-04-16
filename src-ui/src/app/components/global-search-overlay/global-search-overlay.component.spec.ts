import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi, describe, beforeEach, afterEach, it, expect } from 'vitest';
import { SimpleChange } from '@angular/core';

import { GlobalSearchOverlayComponent } from './global-search-overlay.component';
import { SearchService } from '../../services/search.service';
import { SearchResponse } from '../../models/search.model';

const RECENT_QUERIES_KEY = 'dv_recent_queries';

const mockSearchResponse: SearchResponse = {
  count: 2,
  page: 1,
  page_size: 8,
  results: [
    {
      id: 1,
      title: 'Invoice Q1',
      content: 'Some content',
      correspondent: 'Acme',
      document_type: 'Invoice',
      tags: [],
      created: '2024-01-01',
      score: 0.9,
    },
    {
      id: 2,
      title: 'Contract 2024',
      content: 'Contract text',
      correspondent: null,
      document_type: null,
      tags: [],
      created: '2024-02-01',
      score: 0.8,
    },
  ],
  facets: {},
};

function buildSearchService() {
  return {
    search: vi.fn(() => of(mockSearchResponse)),
  };
}

describe('GlobalSearchOverlayComponent', () => {
  let fixture: ComponentFixture<GlobalSearchOverlayComponent>;
  let component: GlobalSearchOverlayComponent;
  let searchSvc: ReturnType<typeof buildSearchService>;

  function simulateOpen(open: boolean) {
    component.open = open;
    component.ngOnChanges({
      open: new SimpleChange(!open, open, false),
    });
    // Do not call fixture.detectChanges() here — it triggers NG0100 in zoneless
    // mode because the RxJS pipe updates focusedIndex synchronously during
    // Angular's second (verification) rendering pass.
  }

  beforeEach(async () => {
    searchSvc = buildSearchService();
    localStorage.removeItem(RECENT_QUERIES_KEY);

    await TestBed.configureTestingModule({
      imports: [GlobalSearchOverlayComponent],
      providers: [
        provideRouter([]),
        { provide: SearchService, useValue: searchSvc },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(GlobalSearchOverlayComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    localStorage.removeItem(RECENT_QUERIES_KEY);
    vi.useRealTimers();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // --- open / close ---

  it('should start closed (open = false)', () => {
    expect(component.open).toBe(false);
  });

  it('should emit closed event when close() is called', () => {
    const spy = vi.fn();
    component.closed.subscribe(spy);
    component.close();
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('should reset state when opened via ngOnChanges', () => {
    component.query = 'old query';
    component.results = mockSearchResponse.results;
    component.searched = true;

    simulateOpen(true);

    expect(component.query).toBe('');
    expect(component.results).toEqual([]);
    expect(component.searched).toBe(false);
  });

  it('should emit closed on Escape key when open', () => {
    component.open = true;
    const spy = vi.fn();
    component.closed.subscribe(spy);

    const event = new KeyboardEvent('keydown', { key: 'Escape' });
    component.onDocumentKeydown(event);

    expect(spy).toHaveBeenCalled();
  });

  it('should not emit closed on Escape when overlay is closed', () => {
    component.open = false;
    const spy = vi.fn();
    component.closed.subscribe(spy);

    const event = new KeyboardEvent('keydown', { key: 'Escape' });
    component.onDocumentKeydown(event);

    expect(spy).not.toHaveBeenCalled();
  });

  // --- search execution ---

  it('should push query to querySubject on onQueryChange', async () => {
    vi.useFakeTimers();
    simulateOpen(true);
    component.onQueryChange('invoice');
    vi.advanceTimersByTime(400); // debounce 300ms + buffer
    await Promise.resolve();
    expect(searchSvc.search).toHaveBeenCalledWith({ query: 'invoice', page_size: 8 });
  });

  it('should clear results when query is empty', async () => {
    vi.useFakeTimers();
    simulateOpen(true);
    component.results = mockSearchResponse.results;
    component.onQueryChange('');
    vi.advanceTimersByTime(400);
    await Promise.resolve();
    expect(component.results).toEqual([]);
    expect(component.loading).toBe(false);
  });

  it('should set focusedIndex to 0 after results returned', async () => {
    vi.useFakeTimers();
    simulateOpen(true);
    component.onQueryChange('invoice');
    vi.advanceTimersByTime(400);
    await Promise.resolve();
    expect(component.focusedIndex).toBe(0);
  });

  // --- moveFocus ---

  it('should move focus down through results', () => {
    simulateOpen(true);
    component.query = 'test';
    component.results = mockSearchResponse.results;
    component.focusedIndex = 0;

    component.moveFocus(1);
    expect(component.focusedIndex).toBe(1);
  });

  it('should wrap focus from last to first', () => {
    simulateOpen(true);
    component.query = 'test';
    component.results = mockSearchResponse.results;
    component.focusedIndex = mockSearchResponse.results.length - 1;

    component.moveFocus(1);
    expect(component.focusedIndex).toBe(0);
  });

  it('should move focus up through results', () => {
    simulateOpen(true);
    component.query = 'test';
    component.results = mockSearchResponse.results;
    component.focusedIndex = 1;

    component.moveFocus(-1);
    expect(component.focusedIndex).toBe(0);
  });

  it('should not change focusedIndex when list is empty', () => {
    component.query = 'test';
    component.results = [];
    component.focusedIndex = -1;
    component.moveFocus(1);
    expect(component.focusedIndex).toBe(-1);
  });

  // --- recent queries from localStorage ---

  it('should load recent queries from localStorage when opened', () => {
    const stored = ['query one', 'query two'];
    localStorage.setItem(RECENT_QUERIES_KEY, JSON.stringify(stored));

    simulateOpen(true);

    expect(component.recentQueries).toEqual(stored);
  });

  it('should start with empty recentQueries when localStorage has nothing', () => {
    simulateOpen(true);
    expect(component.recentQueries).toEqual([]);
  });

  it('should gracefully handle corrupt localStorage data', () => {
    localStorage.setItem(RECENT_QUERIES_KEY, 'not-json{{{');
    simulateOpen(true);
    expect(component.recentQueries).toEqual([]);
  });

  it('should clear recent queries and remove localStorage entry on clearRecent()', () => {
    localStorage.setItem(RECENT_QUERIES_KEY, JSON.stringify(['a', 'b']));
    simulateOpen(true);

    component.clearRecent();

    expect(component.recentQueries).toEqual([]);
    expect(localStorage.getItem(RECENT_QUERIES_KEY)).toBeNull();
  });

  it('applyRecent should set the query and trigger querySubject', async () => {
    vi.useFakeTimers();
    simulateOpen(true);
    component.recentQueries = ['invoice'];

    component.applyRecent('invoice');
    vi.advanceTimersByTime(400);
    await Promise.resolve();

    expect(component.query).toBe('invoice');
    expect(searchSvc.search).toHaveBeenCalledWith({ query: 'invoice', page_size: 8 });
  });

  // --- navigateTo ---

  it('navigateTo should emit closed', () => {
    const spy = vi.fn();
    component.closed.subscribe(spy);
    component.query = 'test doc';

    component.navigateTo(mockSearchResponse.results[0]);

    expect(spy).toHaveBeenCalled();
  });

  // --- ngOnDestroy ---

  it('should unsubscribe on destroy without errors', () => {
    expect(() => component.ngOnDestroy()).not.toThrow();
  });
});
