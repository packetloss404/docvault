import {
  Component,
  ChangeDetectorRef,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { EMPTY, Subject, Subscription } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';
import { SearchService } from '../../services/search.service';
import { UploadService } from '../../services/upload.service';
import { SearchResult } from '../../models/search.model';
import { IconComponent } from '../icon/icon.component';

const RECENT_QUERIES_KEY = 'dv_recent_queries';
const MAX_RECENT_QUERIES = 10;
const DEBOUNCE_MS = 300;

interface PaletteCommand {
  /** Single-glyph affordance, matching the prototype's ↑ / ✎ / ? marks. */
  glyph: string;
  label: string;
  hint?: string;
  keywords: string;
  run: () => void;
}

@Component({
  selector: 'app-global-search-overlay',
  standalone: true,
  imports: [FormsModule, IconComponent],
  template: `
    @if (open) {
      <div
        class="dv-overlay"
        (click)="close()"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <div class="dv-palette" (click)="$event.stopPropagation()">
          <div class="dv-palette__head">
            <span class="dv-palette__caret">&gt;</span>
            <input
              #searchInput
              type="text"
              class="dv-input dv-input--bare"
              placeholder="Search documents, tags, people — or type a command"
              [(ngModel)]="query"
              (ngModelChange)="onQueryChange($event)"
              (keydown.escape)="close()"
              (keydown.arrowDown)="moveFocus(1); $event.preventDefault()"
              (keydown.arrowUp)="moveFocus(-1); $event.preventDefault()"
              (keydown.enter)="activateFocused()"
              autocomplete="off"
              spellcheck="false"
            />
            @if (loading) {
              <span class="dv-spinner" aria-label="Searching"></span>
            }
            <span class="dv-palette__esc">esc</span>
          </div>

          <div class="dv-palette__body">
            @if (!query.trim() && recentQueries.length > 0) {
              <div class="dv-palette__group">
                recent
                <button class="dv-link dv-push" (click)="clearRecent()">clear</button>
              </div>
              @for (q of recentQueries; track q; let i = $index) {
                <div
                  class="dv-palette__row"
                  [class.is-active]="focusedIndex === i"
                  (mouseenter)="focusedIndex = i"
                  (click)="applyRecent(q)"
                >
                  <dv-icon name="search" [size]="14" />
                  <span class="dv-clip">{{ q }}</span>
                </div>
              }
            }

            @if (results.length > 0) {
              <div class="dv-palette__group">documents</div>
              @for (result of results; track result.id; let i = $index) {
                <div
                  class="dv-palette__row"
                  [class.is-active]="focusedIndex === documentOffset + i"
                  (mouseenter)="focusedIndex = documentOffset + i"
                  (click)="navigateTo(result)"
                >
                  <dv-icon name="doc" [size]="14" />
                  <span class="dv-clip">{{ result.title }}</span>
                  <span class="dv-palette__hint">{{ subtitleFor(result) }}</span>
                </div>
              }
            }

            @if (visibleCommands.length > 0) {
              <div class="dv-palette__group">commands</div>
              @for (command of visibleCommands; track command.label; let i = $index) {
                <div
                  class="dv-palette__row"
                  [class.is-active]="focusedIndex === commandOffset + i"
                  (mouseenter)="focusedIndex = commandOffset + i"
                  (click)="runCommand(command)"
                >
                  <span class="dv-palette__caret" style="font-size: 13px">{{
                    command.glyph
                  }}</span>
                  <span class="dv-clip">{{ command.label }}</span>
                  @if (command.hint) {
                    <span class="dv-palette__hint">{{ command.hint }}</span>
                  }
                </div>
              }
            }

            @if (errorMessage) {
              <div class="dv-empty" role="alert">{{ errorMessage }}</div>
            } @else if (query.trim() && !loading && searched && results.length === 0) {
              <div class="dv-empty">
                No documents match <strong>{{ query }}</strong>
              </div>
            }
          </div>

          <div class="dv-palette__foot">
            <span>↑↓ navigate</span>
            <span>↵ open</span>
            <span>esc close</span>
          </div>
        </div>
      </div>
    }
  `,
})
export class GlobalSearchOverlayComponent implements OnChanges, OnDestroy {
  @Input() open = false;
  @Output() closed = new EventEmitter<void>();

  @ViewChild('searchInput') searchInputRef!: ElementRef<HTMLInputElement>;

  private readonly searchService = inject(SearchService);
  private readonly router = inject(Router);
  private readonly uploads = inject(UploadService);
  private readonly changeDetector = inject(ChangeDetectorRef);

  query = '';
  results: SearchResult[] = [];
  recentQueries: string[] = [];
  loading = false;
  searched = false;
  errorMessage = '';
  focusedIndex = -1;

  private readonly commands: PaletteCommand[] = [
    {
      glyph: '↑',
      label: 'Upload document',
      hint: '⇧U',
      keywords: 'upload add ingest file new',
      run: () => this.uploads.pick(),
    },
    {
      glyph: '✎',
      label: 'New signature request',
      keywords: 'sign signature esign request',
      run: () => this.router.navigate(['/signature-requests']),
    },
    {
      glyph: '?',
      label: 'Ask AI across the archive…',
      keywords: 'ask ai question semantic chat',
      run: () =>
        this.router.navigate(['/search'], {
          queryParams: { q: this.query.trim() || null, mode: 'semantic' },
        }),
    },
  ];

  private querySubject = new Subject<string>();
  private searchSub: Subscription;

  constructor() {
    this.searchSub = this.querySubject
      .pipe(
        debounceTime(DEBOUNCE_MS),
        distinctUntilChanged(),
        switchMap((q) => {
          if (!q.trim()) {
            this.results = [];
            this.loading = false;
            this.searched = false;
            this.errorMessage = '';
            this.changeDetector.markForCheck();
            return EMPTY;
          }
          this.loading = true;
          this.errorMessage = '';
          this.changeDetector.markForCheck();
          return this.searchService.search({ query: q, page_size: 8 }).pipe(catchError(() => {
            this.loading = false;
            this.searched = true;
            this.results = [];
            this.errorMessage = 'Search is unavailable. Please try again.';
            this.changeDetector.markForCheck();
            return EMPTY;
          }));
        }),
      )
      .subscribe({
        next: (resp) => {
          this.loading = false;
          this.searched = true;
          this.results = resp.results ?? [];
          this.focusedIndex = this.firstSelectableIndex();
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.searched = true;
          this.results = [];
        },
      });
  }

  /** Commands are filtered by the query so the palette doubles as a launcher. */
  get visibleCommands(): PaletteCommand[] {
    const q = this.query.trim().toLowerCase();
    if (!q) return this.commands;
    return this.commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) || c.keywords.includes(q),
    );
  }

  /** Recent queries occupy indices [0, n) when the input is empty. */
  private get recentCount(): number {
    return this.query.trim() ? 0 : this.recentQueries.length;
  }

  get documentOffset(): number {
    return this.recentCount;
  }

  get commandOffset(): number {
    return this.recentCount + this.results.length;
  }

  private get totalItems(): number {
    return this.commandOffset + this.visibleCommands.length;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['open'] && this.open) {
      this.reset();
      this.loadRecentQueries();
      this.focusedIndex = this.firstSelectableIndex();
      setTimeout(() => this.searchInputRef?.nativeElement?.focus(), 0);
    }
  }

  ngOnDestroy(): void {
    this.searchSub.unsubscribe();
  }

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent): void {
    if (this.open && event.key === 'Escape') {
      event.preventDefault();
      this.close();
    }
  }

  moveFocus(direction: 1 | -1): void {
    const total = this.totalItems;
    if (total === 0) return;
    const start = this.focusedIndex < 0 ? (direction === 1 ? -1 : 0) : this.focusedIndex;
    this.focusedIndex = (start + direction + total) % total;
  }

  activateFocused(): void {
    const index = this.focusedIndex;
    if (index < 0) {
      this.executeSearch();
      return;
    }
    if (index < this.recentCount) {
      this.applyRecent(this.recentQueries[index]);
      return;
    }
    const documentIndex = index - this.documentOffset;
    if (documentIndex >= 0 && documentIndex < this.results.length) {
      this.navigateTo(this.results[documentIndex]);
      return;
    }
    const commandIndex = index - this.commandOffset;
    const command = this.visibleCommands[commandIndex];
    if (command) this.runCommand(command);
  }

  runCommand(command: PaletteCommand): void {
    this.close();
    command.run();
  }

  subtitleFor(result: SearchResult): string {
    return [result.document_type, result.correspondent].filter(Boolean).join(' · ');
  }

  onQueryChange(value: string): void {
    this.focusedIndex = -1;
    this.querySubject.next(value);
  }

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

  clearRecent(): void {
    this.recentQueries = [];
    localStorage.removeItem(RECENT_QUERIES_KEY);
  }

  close(): void {
    this.closed.emit();
  }

  private executeSearch(): void {
    const q = this.query.trim();
    if (!q) return;
    this.saveRecentQuery(q);
    this.router.navigate(['/search'], { queryParams: { q, page: 1 } });
    this.close();
  }

  private firstSelectableIndex(): number {
    return this.totalItems > 0 ? 0 : -1;
  }

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

  private reset(): void {
    this.query = '';
    this.results = [];
    this.loading = false;
    this.searched = false;
    this.focusedIndex = -1;
  }
}
