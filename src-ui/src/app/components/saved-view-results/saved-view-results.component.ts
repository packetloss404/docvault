import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { SearchService } from '../../services/search.service';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-saved-view-results',
  standalone: true,
  imports: [CommonModule, RouterModule, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-section svr-head">
          <h1 class="dv-h1 dv-h1--sm">{{ viewName() || 'Saved view results' }}</h1>
          @if (!loading() && !error() && results().length) {
            <span class="dv-meta"
              >{{ totalCount() }} document{{ totalCount() !== 1 ? 's' : '' }}</span
            >
          }
          <a class="dv-btn dv-btn--ghost dv-btn--sm dv-push" routerLink="/saved-views"
            >← all views</a
          >
        </div>

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <div>Loading results…</div>
          </div>
        } @else if (error()) {
          <div class="svr-error" role="alert">{{ error() }}</div>
        } @else if (results().length === 0) {
          <div class="dv-empty">No documents match this view's filters.</div>
        } @else {
          <div
            class="dv-thead dv-grid"
            style="--dv-cols: minmax(0,1fr) 130px 150px 170px"
          >
            <span>title</span>
            <span>created</span>
            <span>type</span>
            <span>correspondent</span>
          </div>

          @for (doc of results(); track doc.id) {
            <a
              class="dv-row dv-grid"
              style="--dv-cols: minmax(0,1fr) 130px 150px 170px"
              [routerLink]="['/documents', doc.id]"
            >
              <span class="dv-clip svr-title">{{
                doc.title || doc.original_filename || 'Untitled'
              }}</span>
              <span class="dv-ts">{{ formatDate(doc.created) }}</span>
              <span>
                @if (doc.document_type_name) {
                  <span class="dv-chip dv-chip--well">{{ doc.document_type_name }}</span>
                }
              </span>
              <span class="dv-meta dv-clip">{{ doc.correspondent_name || '' }}</span>
            </a>
          }

          @if (totalPages() > 1) {
            <nav class="dv-pager" aria-label="Result pages">
              <span [class.is-disabled]="currentPage() <= 1" (click)="goToPage(currentPage() - 1)"
                >prev</span
              >
              @for (p of pageNumbers(); track p) {
                <span [class.is-current]="p === currentPage()" (click)="goToPage(p)">{{ p }}</span>
              }
              <span
                [class.is-disabled]="currentPage() >= totalPages()"
                (click)="goToPage(currentPage() + 1)"
                >next</span
              >
            </nav>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        display: contents;
      }

      dv-subnav {
        display: block;
        margin-bottom: 16px;
      }

      .svr-head {
        align-items: baseline;
        gap: 12px;
      }

      .svr-title {
        font-size: 13.5px;
        font-weight: 500;
        color: var(--text);
      }

      .svr-error {
        background: var(--danger-dim);
        border: 1px solid var(--danger);
        border-radius: 9px;
        padding: 11px 13px;
        color: var(--danger);
        font-size: 12.5px;
        line-height: 1.45;
      }

      .dv-pager .is-disabled {
        opacity: 0.4;
        cursor: default;
      }
    `,
  ],
})
export class SavedViewResultsComponent implements OnInit {
  viewId = 0;
  viewName = signal('');
  results = signal<any[]>([]);
  totalCount = signal(0);
  currentPage = signal(1);
  pageSize = signal(25);
  loading = signal(false);
  error = signal('');

  constructor(
    private route: ActivatedRoute,
    private searchService: SearchService,
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      this.viewId = +params['viewId'];
      this.loadViewName();
      this.loadResults();
    });
  }

  loadViewName(): void {
    this.searchService.getSavedView(this.viewId).subscribe({
      next: (view) => this.viewName.set(view.name),
      error: () => this.viewName.set('Saved View'),
    });
  }

  loadResults(): void {
    this.loading.set(true);
    this.error.set('');
    this.searchService.executeSavedView(this.viewId, this.currentPage()).subscribe({
      next: (res) => {
        this.results.set(res.results as any[]);
        this.totalCount.set(res.count);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load saved view results. The view may not exist or you may not have permission.');
        this.loading.set(false);
      },
    });
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadResults();
  }

  totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize());
  }

  pageNumbers(): number[] {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }

  formatDate(dateString: string): string {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
}
