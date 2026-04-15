import {
  Component,
  EventEmitter,
  HostListener,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ElementRef,
  ViewChild,
  AfterViewInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';
import { SearchService } from '../../services/search.service';
import { SearchResult } from '../../models/search.model';

const RECENT_QUERIES_KEY = 'dv_recent_queries';
const MAX_RECENT_QUERIES = 10;
const DEBOUNCE_MS = 300;

@Component({
  selector: 'app-global-search-overlay',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    @if (open) {
      <!-- Backdrop -->
      <div
        class="gso-backdrop"
        (click)="close()"
        aria-hidden="true"
      ></div>

      <!-- Palette panel -->
      <div
        class="gso-panel shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-label="Global search"
        #panel
      >
        <!-- Search input row -->
        <div class="gso-input-row d-flex align-items-center px-3 py-2 border-bottom">
          <i class="bi bi-search text-secondary me-2 fs-5"></i>
          <input
            #searchInput
            type="text"
            class="form-control border-0 shadow-none bg-transparent fs-5 p-0"
            placeholder="Search documents…"
            [(ngModel)]="query"
            (ngModelChange)="onQueryChange($event)"
            (keydown.escape)="close()"
            (keydown.arrowDown)="moveFocus(1)"
            (keydown.arrowUp)="moveFocus(-1)"
            (keydown.enter)="activateFocused()"
            autocomplete="off"
            spellcheck="false"
          />
          @if (loading) {
            <div class="spinner-border spinner-border-sm text-secondary ms-2" role="status">
              <span class="visually-hidden">Searching…</span>
            </div>
          }
          <kbd class="ms-2 text-secondary small d-none d-sm-inline">Esc</kbd>
        </div>

        <!-- Results / recent queries body -->
        <div class="gso-body overflow-auto">

          <!-- Recent queries (shown when input is empty and there are recents) -->
          @if (!query.trim() && recentQueries.length > 0) {
            <div class="gso-section-label px-3 pt-2 pb-1 small text-secondary text-uppercase fw-semibold d-flex justify-content-between align-items-center">
              <span>Recent searches</span>
              <button class="btn btn-link btn-sm p-0 text-secondary text-decoration-none" (click)="clearRecent()">
                Clear
              </button>
            </div>
            @for (q of recentQueries; track q; let i = $index) {
              <div
                class="gso-item d-flex align-items-center px-3 py-2"
                [class.gso-item--focused]="focusedIndex === i"
                (mouseenter)="focusedIndex = i"
                (click)="applyRecent(q)"
                role="option"
                [attr.aria-selected]="focusedIndex === i"
              >
                <i class="bi bi-clock-history me-3 text-secondary flex-shrink-0"></i>
                <span class="text-truncate">{{ q }}</span>
              </div>
            }
          }

          <!-- Search results -->
          @if (query.trim() && results.length > 0) {
            <div class="gso-section-label px-3 pt-2 pb-1 small text-secondary text-uppercase fw-semibold">
              Documents
            </div>
            @for (result of results; track result.id; let i = $index) {
              <div
                class="gso-item d-flex align-items-start px-3 py-2"
                [class.gso-item--focused]="focusedIndex === i"
                (mouseenter)="focusedIndex = i"
                (click)="navigateTo(result)"
                role="option"
                [attr.aria-selected]="focusedIndex === i"
              >
                <i class="bi bi-file-earmark-text me-3 text-secondary flex-shrink-0 pt-1"></i>
                <div class="overflow-hidden">
                  <div class="fw-medium text-truncate">{{ result.title }}</div>
                  <div class="small text-secondary d-flex gap-2 mt-1 flex-wrap">
                    @if (result.document_type) {
                      <span>
                        <i class="bi bi-tag me-1"></i>{{ result.document_type }}
                      </span>
                    }
                    @if (result.correspondent) {
                      <span>
                        <i class="bi bi-person me-1"></i>{{ result.correspondent }}
                      </span>
                    }
                    @if (!result.document_type && !result.correspondent) {
                      <span class="fst-italic">No type or correspondent</span>
                    }
                  </div>
                </div>
              </div>
            }
          }

          <!-- No results -->
          @if (query.trim() && !loading && results.length === 0 && searched) {
            <div class="gso-empty px-3 py-4 text-center text-secondary">
              <i class="bi bi-search fs-3 d-block mb-2"></i>
              No documents found for <strong>{{ query }}</strong>
            </div>
          }

          <!-- Empty state with no recent queries -->
          @if (!query.trim() && recentQueries.length === 0) {
            <div class="gso-empty px-3 py-4 text-center text-secondary">
              <i class="bi bi-keyboard fs-3 d-block mb-2"></i>
              Start typing to search documents
            </div>
          }

        </div>

        <!-- Footer hint -->
        <div class="gso-footer d-flex gap-3 px-3 py-2 border-top small text-secondary">
          <span><kbd>↑↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    }
  `,
  styles: [`
    .gso-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.55);
      z-index: 1050;
      animation: gso-fade-in 0.15s ease;
    }

    .gso-panel {
      position: fixed;
      top: 15vh;
      left: 50%;
      transform: translateX(-50%);
      width: min(640px, 92vw);
      max-height: 70vh;
      display: flex;
      flex-direction: column;
      z-index: 1051;
      border-radius: 0.75rem;
      overflow: hidden;
      animation: gso-slide-in 0.15s ease;
      background: var(--bs-body-bg, #fff);
      border: 1px solid var(--bs-border-color, #dee2e6);
    }

    .gso-input-row input:focus {
      outline: none;
      box-shadow: none;
    }

    .gso-body {
      flex: 1;
      min-height: 0;
    }

    .gso-item {
      cursor: pointer;
      transition: background-color 0.08s ease;
    }

    .gso-item:hover,
    .gso-item--focused {
      background-color: var(--bs-tertiary-bg, #f8f9fa);
    }

    [data-bs-theme="dark"] .gso-item:hover,
    [data-bs-theme="dark"] .gso-item--focused {
      background-color: var(--bs-secondary-bg, #343a40);
    }

    .gso-section-label {
      letter-spacing: 0.05em;
    }

    .gso-empty {
      min-height: 120px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .gso-footer kbd {
      font-size: 0.7rem;
      padding: 1px 4px;
      border-radius: 3px;
      border: 1px solid var(--bs-border-color, #dee2e6);
      background: var(--bs-secondary-bg, #f8f9fa);
    }

    @keyframes gso-fade-in {
      from { opacity: 0; }
      to   { opacity: 1; }
    }

    @keyframes gso-slide-in {
      from { opacity: 0; transform: translateX(-50%) translateY(-12px); }
      to   { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
  `],
})
export class GlobalSearchOverlayComponent implements OnChanges, OnDestroy, AfterViewInit {
  @Input() open = false;
  @Output() closed = new EventEmitter<void>();

  @ViewChild('searchInput') searchInputRef!: ElementRef<HTMLInputElement>;

  query = '';
  results: SearchResult[] = [];
  recentQueries: string[] = [];
  loading = false;
  searched = false;
  focusedIndex = -1;

  private querySubject = new Subject<string>();
  private searchSub: Subscription;

  constructor(
    private searchService: SearchService,
    private router: Router,
  ) {
    this.searchSub = this.querySubject.pipe(
      debounceTime(DEBOUNCE_MS),
      distinctUntilChanged(),
      switchMap((q) => {
        if (!q.trim()) {
          this.results = [];
          this.loading = false;
          this.searched = false;
          return [];
        }
        this.loading = true;
        return this.searchService.search({ query: q, page_size: 8 });
      }),
    ).subscribe({
      next: (resp) => {
        this.loading = false;
        this.searched = true;
        this.results = resp.results ?? [];
        this.focusedIndex = this.results.length > 0 ? 0 : -1;
      },
      error: () => {
        this.loading = false;
        this.searched = true;
        this.results = [];
      },
    });
  }

  ngAfterViewInit(): void {
    // Focus is triggered via ngOnChanges when open becomes true;
    // AfterViewInit is too early at component creation.
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['open']) {
      if (this.open) {
        this.reset();
        this.loadRecentQueries();
        // Defer focus until the template has rendered
        setTimeout(() => this.searchInputRef?.nativeElement?.focus(), 0);
      }
    }
  }

  ngOnDestroy(): void {
    this.searchSub.unsubscribe();
  }

  // ---- keyboard navigation inside the panel ----

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent): void {
    if (!this.open) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      this.close();
    }
  }

  moveFocus(direction: 1 | -1): void {
    const listLength = this.query.trim()
      ? this.results.length
      : this.recentQueries.length;
    if (listLength === 0) return;
    this.focusedIndex = (this.focusedIndex + direction + listLength) % listLength;
  }

  activateFocused(): void {
    if (this.query.trim()) {
      // Navigate to focused search result, or run search if nothing focused
      if (this.focusedIndex >= 0 && this.results[this.focusedIndex]) {
        this.navigateTo(this.results[this.focusedIndex]);
      } else if (this.query.trim()) {
        this.executeSearch();
      }
    } else {
      // Apply focused recent query
      if (this.focusedIndex >= 0 && this.recentQueries[this.focusedIndex]) {
        this.applyRecent(this.recentQueries[this.focusedIndex]);
      }
    }
  }

  // ---- search ----

  onQueryChange(value: string): void {
    this.focusedIndex = -1;
    this.querySubject.next(value);
  }

  private executeSearch(): void {
    const q = this.query.trim();
    if (!q) return;
    this.saveRecentQuery(q);
    this.router.navigate(['/search'], { queryParams: { q, page: 1 } });
    this.close();
  }

  // ---- navigation ----

  navigateTo(result: SearchResult): void {
    this.saveRecentQuery(this.query.trim());
    this.router.navigate(['/documents', result.id]);
    this.close();
  }

  applyRecent(q: string): void {
    this.query = q;
    this.onQueryChange(q);
    setTimeout(() => this.searchInputRef?.nativeElement?.focus(), 0);
  }

  // ---- recent queries ----

  private loadRecentQueries(): void {
    try {
      const stored = localStorage.getItem(RECENT_QUERIES_KEY);
      this.recentQueries = stored ? (JSON.parse(stored) as string[]) : [];
    } catch {
      this.recentQueries = [];
    }
  }

  private saveRecentQuery(q: string): void {
    if (!q) return;
    const updated = [q, ...this.recentQueries.filter((r) => r !== q)].slice(
      0,
      MAX_RECENT_QUERIES,
    );
    this.recentQueries = updated;
    localStorage.setItem(RECENT_QUERIES_KEY, JSON.stringify(updated));
  }

  clearRecent(): void {
    this.recentQueries = [];
    localStorage.removeItem(RECENT_QUERIES_KEY);
  }

  // ---- overlay control ----

  close(): void {
    this.closed.emit();
  }

  private reset(): void {
    this.query = '';
    this.results = [];
    this.loading = false;
    this.searched = false;
    this.focusedIndex = -1;
  }
}
