import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { SearchService } from '../../services/search.service';

@Component({
  selector: 'app-saved-view-results',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3 class="mb-0">{{ viewName() || 'Saved View Results' }}</h3>
      <a routerLink="/saved-views" class="btn btn-sm btn-outline-secondary">
        <i class="bi bi-arrow-left me-1"></i>All Views
      </a>
    </div>

    @if (loading()) {
      <div class="text-center py-5">
        <div class="spinner-border"></div>
        <p class="text-muted mt-2">Loading results...</p>
      </div>
    } @else if (error()) {
      <div class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-1"></i>
        {{ error() }}
      </div>
    } @else if (results().length === 0) {
      <div class="text-center py-5 text-muted">
        <i class="bi bi-inbox" style="font-size: 3rem;"></i>
        <p class="mt-2">No documents match this view's filters.</p>
      </div>
    } @else {
      <p class="text-muted mb-3">{{ totalCount() }} document{{ totalCount() !== 1 ? 's' : '' }}</p>

      <div class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Title</th>
              <th>Created</th>
              <th>Type</th>
              <th>Correspondent</th>
            </tr>
          </thead>
          <tbody>
            @for (doc of results(); track doc.id) {
              <tr>
                <td>
                  <a [routerLink]="['/documents', doc.id]" class="text-decoration-none">
                    {{ doc.title || doc.original_filename || 'Untitled' }}
                  </a>
                </td>
                <td class="text-muted small">{{ formatDate(doc.created) }}</td>
                <td>
                  @if (doc.document_type_name) {
                    <span class="badge bg-light text-dark">{{ doc.document_type_name }}</span>
                  }
                </td>
                <td class="text-muted small">{{ doc.correspondent_name || '' }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      @if (totalPages() > 1) {
        <nav>
          <ul class="pagination pagination-sm justify-content-center">
            <li class="page-item" [class.disabled]="currentPage() <= 1">
              <button class="page-link" (click)="goToPage(currentPage() - 1)">&laquo;</button>
            </li>
            @for (p of pageNumbers(); track p) {
              <li class="page-item" [class.active]="p === currentPage()">
                <button class="page-link" (click)="goToPage(p)">{{ p }}</button>
              </li>
            }
            <li class="page-item" [class.disabled]="currentPage() >= totalPages()">
              <button class="page-link" (click)="goToPage(currentPage() + 1)">&raquo;</button>
            </li>
          </ul>
        </nav>
      }
    }
  `,
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
