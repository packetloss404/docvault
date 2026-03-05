import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchSynonym } from '../../models/analytics.model';

@Component({
  selector: 'app-synonym-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Synonym Manager</h2>
      <button class="btn btn-primary" (click)="showForm = !showForm">
        <i class="bi bi-plus-lg me-1"></i>
        {{ showForm ? 'Cancel' : 'Add Synonym Group' }}
      </button>
    </div>

    @if (showForm) {
      <div class="card mb-4">
        <div class="card-body">
          <h5 class="card-title">{{ editingId ? 'Edit' : 'Create' }} Synonym Group</h5>
          <form (ngSubmit)="onSave()">
            <div class="mb-3">
              <label class="form-label">Terms (comma-separated)</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="formTerms"
                name="terms"
                placeholder="e.g. invoice, bill, receipt"
                required
              />
              <div class="form-text">Enter synonymous terms separated by commas. All terms in a group will be treated as equivalent in search.</div>
            </div>
            <div class="form-check form-switch mb-3">
              <input
                class="form-check-input"
                type="checkbox"
                [(ngModel)]="formEnabled"
                name="enabled"
                id="synEnabledSwitch"
              />
              <label class="form-check-label" for="synEnabledSwitch">Enabled</label>
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
              <th>Terms</th>
              <th>Status</th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (synonym of synonyms(); track synonym.id) {
              <tr>
                <td>
                  @for (term of synonym.terms; track term) {
                    <span class="badge bg-info text-dark me-1">{{ term }}</span>
                  }
                </td>
                <td>
                  <div class="form-check form-switch">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      [checked]="synonym.enabled"
                      (change)="toggleEnabled(synonym)"
                    />
                  </div>
                </td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-primary me-1" (click)="onEdit(synonym)" title="Edit">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" (click)="onDelete(synonym)" title="Delete">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="3" class="text-center text-muted py-4">
                  No synonym groups defined. Create one to improve search recall.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
})
export class SynonymManagerComponent implements OnInit {
  synonyms = signal<SearchSynonym[]>([]);
  loading = signal(true);
  saving = signal(false);

  showForm = false;
  editingId: number | null = null;
  formTerms = '';
  formEnabled = true;

  constructor(private analyticsService: AnalyticsService) {}

  ngOnInit(): void {
    this.loadSynonyms();
  }

  loadSynonyms(): void {
    this.loading.set(true);
    this.analyticsService.getSynonyms().subscribe({
      next: (resp) => {
        this.synonyms.set(resp.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onEdit(synonym: SearchSynonym): void {
    this.editingId = synonym.id;
    this.formTerms = synonym.terms.join(', ');
    this.formEnabled = synonym.enabled;
    this.showForm = true;
  }

  cancelEdit(): void {
    this.editingId = null;
    this.formTerms = '';
    this.formEnabled = true;
    this.showForm = false;
  }

  onSave(): void {
    const terms = this.formTerms
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    if (terms.length < 2) return;

    this.saving.set(true);
    const data: Partial<SearchSynonym> = {
      terms,
      enabled: this.formEnabled,
    };

    const request = this.editingId
      ? this.analyticsService.updateSynonym(this.editingId, data)
      : this.analyticsService.createSynonym(data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.cancelEdit();
        this.loadSynonyms();
      },
      error: () => this.saving.set(false),
    });
  }

  toggleEnabled(synonym: SearchSynonym): void {
    this.analyticsService
      .updateSynonym(synonym.id, { enabled: !synonym.enabled })
      .subscribe({
        next: () => this.loadSynonyms(),
      });
  }

  onDelete(synonym: SearchSynonym): void {
    if (!confirm(`Delete synonym group: ${synonym.terms.join(', ')}?`)) return;
    this.analyticsService.deleteSynonym(synonym.id).subscribe({
      next: () => this.loadSynonyms(),
    });
  }
}
