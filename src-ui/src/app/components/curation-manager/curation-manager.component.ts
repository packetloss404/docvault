import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchService } from '../../services/search.service';
import { SearchCuration } from '../../models/analytics.model';

@Component({
  selector: 'app-curation-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Search Curations</h2>
      <button class="btn btn-primary" (click)="showForm = !showForm">
        <i class="bi bi-plus-lg me-1"></i>
        {{ showForm ? 'Cancel' : 'New Curation' }}
      </button>
    </div>

    @if (showForm) {
      <div class="card mb-4">
        <div class="card-body">
          <h5 class="card-title">{{ editingId ? 'Edit' : 'Create' }} Curation</h5>
          <form (ngSubmit)="onSave()">
            <div class="mb-3">
              <label class="form-label">Query Text</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="formQueryText"
                name="queryText"
                placeholder="Enter the search query to curate"
                required
              />
            </div>
            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label class="form-label">Pinned Document IDs</label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formPinnedIds"
                  name="pinnedIds"
                  placeholder="e.g. 1, 5, 12"
                />
                <div class="form-text">Comma-separated document IDs to pin at the top of results.</div>
              </div>
              <div class="col-md-6">
                <label class="form-label">Hidden Document IDs</label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formHiddenIds"
                  name="hiddenIds"
                  placeholder="e.g. 3, 7"
                />
                <div class="form-text">Comma-separated document IDs to hide from results.</div>
              </div>
            </div>

            <!-- Document Search Helper -->
            <div class="mb-3">
              <label class="form-label">Search for Documents</label>
              <div class="input-group">
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="docSearchQuery"
                  name="docSearchQuery"
                  placeholder="Search documents to find IDs..."
                />
                <button class="btn btn-outline-secondary" type="button" (click)="searchDocuments()">
                  <i class="bi bi-search"></i>
                </button>
              </div>
              @if (searchResults().length > 0) {
                <div class="list-group mt-2" style="max-height: 200px; overflow-y: auto;">
                  @for (doc of searchResults(); track doc.id) {
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                      <span><strong>#{{ doc.id }}</strong> - {{ doc.title }}</span>
                      <div>
                        <button class="btn btn-sm btn-outline-success me-1" type="button" (click)="addPinned(doc.id)" title="Pin">
                          <i class="bi bi-pin-angle"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" type="button" (click)="addHidden(doc.id)" title="Hide">
                          <i class="bi bi-eye-slash"></i>
                        </button>
                      </div>
                    </div>
                  }
                </div>
              }
            </div>

            <div class="form-check form-switch mb-3">
              <input
                class="form-check-input"
                type="checkbox"
                [(ngModel)]="formEnabled"
                name="enabled"
                id="curationEnabledSwitch"
              />
              <label class="form-check-label" for="curationEnabledSwitch">Enabled</label>
            </div>
            <button type="submit" class="btn btn-success me-2" [disabled]="saving()">
              <i class="bi bi-check-lg me-1"></i>{{ editingId ? 'Update' : 'Create' }}
            </button>
            <button type="button" class="btn btn-secondary" (click)="cancelEdit()">Cancel</button>
          </form>
        </div>
      </div>
    }

    @if (loading()) {
      <div class="text-center py-5">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else {
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead>
            <tr>
              <th>Query</th>
              <th>Pinned</th>
              <th>Hidden</th>
              <th>Status</th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (curation of curations(); track curation.id) {
              <tr>
                <td class="fw-semibold"><code>{{ curation.query_text }}</code></td>
                <td>
                  @if (curation.pinned_documents.length > 0) {
                    <span class="badge bg-success">{{ curation.pinned_documents.length }} pinned</span>
                  } @else {
                    <span class="text-muted">-</span>
                  }
                </td>
                <td>
                  @if (curation.hidden_documents.length > 0) {
                    <span class="badge bg-danger">{{ curation.hidden_documents.length }} hidden</span>
                  } @else {
                    <span class="text-muted">-</span>
                  }
                </td>
                <td>
                  <div class="form-check form-switch">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      [checked]="curation.enabled"
                      (change)="toggleEnabled(curation)"
                    />
                  </div>
                </td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-primary me-1" (click)="onEdit(curation)" title="Edit">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" (click)="onDelete(curation)" title="Delete">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5" class="text-center text-muted py-4">
                  No curations defined. Create one to customize search results for specific queries.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
})
export class CurationManagerComponent implements OnInit {
  curations = signal<SearchCuration[]>([]);
  loading = signal(true);
  saving = signal(false);
  searchResults = signal<{ id: number; title: string }[]>([]);

  showForm = false;
  editingId: number | null = null;
  formQueryText = '';
  formPinnedIds = '';
  formHiddenIds = '';
  formEnabled = true;
  docSearchQuery = '';

  constructor(
    private analyticsService: AnalyticsService,
    private searchService: SearchService,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.loadCurations();
    // Pre-fill query from query params (e.g., from search analytics "Create Curation" link)
    const queryParam = this.route.snapshot.queryParamMap.get('query');
    if (queryParam) {
      this.formQueryText = queryParam;
      this.showForm = true;
    }
  }

  loadCurations(): void {
    this.loading.set(true);
    this.analyticsService.getCurations().subscribe({
      next: (resp) => {
        this.curations.set(resp.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onEdit(curation: SearchCuration): void {
    this.editingId = curation.id;
    this.formQueryText = curation.query_text;
    this.formPinnedIds = curation.pinned_documents.join(', ');
    this.formHiddenIds = curation.hidden_documents.join(', ');
    this.formEnabled = curation.enabled;
    this.showForm = true;
  }

  cancelEdit(): void {
    this.editingId = null;
    this.formQueryText = '';
    this.formPinnedIds = '';
    this.formHiddenIds = '';
    this.formEnabled = true;
    this.showForm = false;
    this.searchResults.set([]);
  }

  parseIds(input: string): number[] {
    return input
      .split(',')
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0);
  }

  onSave(): void {
    if (!this.formQueryText.trim()) return;
    this.saving.set(true);

    const data: Partial<SearchCuration> = {
      query_text: this.formQueryText.trim(),
      pinned_documents: this.parseIds(this.formPinnedIds),
      hidden_documents: this.parseIds(this.formHiddenIds),
      enabled: this.formEnabled,
    };

    const request = this.editingId
      ? this.analyticsService.updateCuration(this.editingId, data)
      : this.analyticsService.createCuration(data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.cancelEdit();
        this.loadCurations();
      },
      error: () => this.saving.set(false),
    });
  }

  toggleEnabled(curation: SearchCuration): void {
    this.analyticsService
      .updateCuration(curation.id, { enabled: !curation.enabled })
      .subscribe({
        next: () => this.loadCurations(),
      });
  }

  onDelete(curation: SearchCuration): void {
    if (!confirm(`Delete curation for query "${curation.query_text}"?`)) return;
    this.analyticsService.deleteCuration(curation.id).subscribe({
      next: () => this.loadCurations(),
    });
  }

  searchDocuments(): void {
    if (!this.docSearchQuery.trim()) return;
    this.searchService
      .search({ query: this.docSearchQuery.trim(), page_size: 10 })
      .subscribe({
        next: (resp) => {
          this.searchResults.set(
            resp.results.map((r) => ({ id: r.id, title: r.title })),
          );
        },
      });
  }

  addPinned(docId: number): void {
    const current = this.parseIds(this.formPinnedIds);
    if (!current.includes(docId)) {
      current.push(docId);
      this.formPinnedIds = current.join(', ');
    }
  }

  addHidden(docId: number): void {
    const current = this.parseIds(this.formHiddenIds);
    if (!current.includes(docId)) {
      current.push(docId);
      this.formHiddenIds = current.join(', ');
    }
  }
}
