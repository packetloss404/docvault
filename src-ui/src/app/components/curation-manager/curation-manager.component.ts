import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchService } from '../../services/search.service';
import { SearchCuration } from '../../models/analytics.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-curation-manager',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner">
        <dv-subnav />

        <div class="dv-section cu-head">
          <span class="dv-eyebrow"
            >{{ curations().length }} curation{{ curations().length !== 1 ? 's' : '' }}</span
          >
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--md dv-push"
            (click)="showForm = !showForm"
          >
            {{ showForm ? 'Cancel' : '+ New curation' }}
          </button>
        </div>

        @if (showForm) {
          <form class="dv-card dv-card--r10 cu-form" (ngSubmit)="onSave()">
            <div class="dv-card__head">
              <span class="dv-card__title">{{ editingId ? 'Edit' : 'Create' }} curation</span>
            </div>
            <div class="cu-form__body">
              <div>
                <label class="dv-field__label" for="cu-query">query text</label>
                <input
                  type="text"
                  id="cu-query"
                  class="dv-input dv-input--mono"
                  [(ngModel)]="formQueryText"
                  name="queryText"
                  placeholder="the search query to curate"
                  required
                />
              </div>

              <div class="cu-fields">
                <div>
                  <label class="dv-field__label" for="cu-pinned">pinned document ids</label>
                  <input
                    type="text"
                    id="cu-pinned"
                    class="dv-input dv-input--mono"
                    [(ngModel)]="formPinnedIds"
                    name="pinnedIds"
                    placeholder="1, 5, 12"
                  />
                  <div class="dv-meta cu-hint">pinned to the top of results, in order</div>
                </div>
                <div>
                  <label class="dv-field__label" for="cu-hidden">hidden document ids</label>
                  <input
                    type="text"
                    id="cu-hidden"
                    class="dv-input dv-input--mono"
                    [(ngModel)]="formHiddenIds"
                    name="hiddenIds"
                    placeholder="3, 7"
                  />
                  <div class="dv-meta cu-hint">removed from results for this query</div>
                </div>
              </div>

              <!-- Document lookup helper -->
              <div>
                <span class="dv-field__label">find documents</span>
                <div class="cu-lookup">
                  <input
                    type="text"
                    class="dv-input dv-input--r7"
                    [(ngModel)]="docSearchQuery"
                    name="docSearchQuery"
                    placeholder="Search documents to find their ids…"
                    aria-label="Search documents"
                  />
                  <button
                    type="button"
                    class="dv-btn dv-btn--ghost dv-btn--sm"
                    (click)="searchDocuments()"
                  >
                    Search
                  </button>
                </div>

                @if (searchResults().length > 0) {
                  <div class="dv-well cu-hits">
                    @for (doc of searchResults(); track doc.id) {
                      <div class="cu-hit">
                        <span class="dv-mono dv-faint">#{{ doc.id }}</span>
                        <span class="dv-clip">{{ doc.title }}</span>
                        <button
                          type="button"
                          class="cu-action dv-push"
                          title="Pin"
                          (click)="addPinned(doc.id)"
                        >
                          📌 pin
                        </button>
                        <button
                          type="button"
                          class="cu-action cu-action--danger"
                          title="Hide"
                          (click)="addHidden(doc.id)"
                        >
                          ✕ hide
                        </button>
                      </div>
                    }
                  </div>
                }
              </div>

              <div class="cu-switch">
                <button
                  type="button"
                  class="dv-toggle"
                  [class.is-on]="formEnabled"
                  role="switch"
                  [attr.aria-checked]="formEnabled"
                  aria-label="Enabled"
                  (click)="formEnabled = !formEnabled"
                ></button>
                <span>Enabled</span>
              </div>

              <div class="cu-actions">
                <button
                  type="submit"
                  class="dv-btn dv-btn--primary dv-btn--md"
                  [disabled]="saving()"
                >
                  {{ editingId ? 'Update' : 'Create' }}
                </button>
                <button
                  type="button"
                  class="dv-btn dv-btn--ghost dv-btn--md"
                  (click)="cancelEdit()"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        }

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <span class="dv-sr">Loading…</span>
          </div>
        } @else {
          <div class="cu-list">
            @for (curation of curations(); track curation.id) {
              <div class="dv-card dv-card--r10 cu-card">
                <div class="cu-card__head">
                  <span class="cu-query">“{{ curation.query_text }}”</span>
                  <span class="dv-push"></span>
                  @if (!curation.enabled) {
                    <span class="dv-chip dv-chip--warn dv-chip--upper">disabled</span>
                  }
                  <button
                    type="button"
                    class="dv-toggle"
                    [class.is-on]="curation.enabled"
                    role="switch"
                    [attr.aria-checked]="curation.enabled"
                    aria-label="Toggle enabled"
                    (click)="toggleEnabled(curation)"
                  ></button>
                  <button type="button" class="cu-action" (click)="onEdit(curation)">edit</button>
                  <button
                    type="button"
                    class="cu-action cu-action--danger"
                    title="Delete"
                    aria-label="Delete curation"
                    (click)="onDelete(curation)"
                  >
                    ✕
                  </button>
                </div>

                <div class="cu-card__body">
                  @if (curation.pinned_documents.length > 0) {
                    <span class="cu-pin">
                      <span class="cu-pin__glyph" aria-hidden="true">📌</span>
                      <span class="cu-pin__label"
                        >{{ curation.pinned_documents.length }} pinned</span
                      >
                      <span class="dv-meta">#{{ curation.pinned_documents.join(' #') }}</span>
                    </span>
                  }
                  @if (curation.hidden_documents.length > 0) {
                    <span class="dv-chip dv-chip--danger"
                      >{{ curation.hidden_documents.length }} hidden</span
                    >
                  }
                  @if (
                    curation.pinned_documents.length === 0 &&
                    curation.hidden_documents.length === 0
                  ) {
                    <span class="dv-meta">no pins or hides yet</span>
                  }
                </div>
              </div>
            } @empty {
              <div class="dv-empty">
                No curations defined. Create one to shape results for a specific query.
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
  styles: [
    `
      $mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

      :host {
        display: contents;
      }

      dv-subnav {
        display: block;
        margin-bottom: 16px;
      }

      .cu-head {
        align-items: center;
      }

      .cu-form {
        margin-bottom: 18px;

        &__body {
          padding: 16px 18px;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
      }

      .cu-fields {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px 14px;
      }

      .cu-hint {
        margin-top: 6px;
      }

      .cu-lookup {
        display: flex;
        gap: 8px;
        align-items: center;

        .dv-input {
          flex: 1;
          min-width: 0;
        }
      }

      .cu-hits {
        margin-top: 8px;
        max-height: 200px;
        overflow-y: auto;
        padding: 4px 0;
      }

      .cu-hit {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 7px 12px;
        font-size: 12.5px;
        min-width: 0;
      }

      .cu-action {
        background: none;
        border: none;
        padding: 0 2px;
        font: 400 11px #{$mono};
        color: var(--faint);
        cursor: pointer;
        white-space: nowrap;

        &:hover {
          color: var(--text);
        }

        &--danger:hover {
          color: var(--danger);
        }
      }

      .cu-actions {
        display: flex;
        gap: 8px;
      }

      .cu-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .cu-card {
        padding: 13px 17px;

        &__head {
          display: flex;
          align-items: center;
          gap: 10px;
          min-width: 0;
        }

        &__body {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 9px;
          flex-wrap: wrap;
        }
      }

      .cu-query {
        font: 400 12.5px #{$mono};
        color: var(--accent-text);
        min-width: 0;
        overflow-wrap: anywhere;
      }

      .cu-pin {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 12.5px;

        &__glyph {
          color: var(--warn);
        }

        &__label {
          font-weight: 500;
        }
      }
    `,
  ],
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
