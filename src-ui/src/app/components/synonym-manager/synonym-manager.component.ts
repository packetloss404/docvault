import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchSynonym } from '../../models/analytics.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-synonym-manager',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner">
        <dv-subnav />

        <div class="dv-section sy-head">
          <span class="dv-eyebrow"
            >{{ synonyms().length }} synonym group{{
              synonyms().length !== 1 ? 's' : ''
            }}</span
          >
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--md dv-push"
            (click)="showForm = !showForm"
          >
            {{ showForm ? 'Cancel' : '+ Add synonym group' }}
          </button>
        </div>

        @if (showForm) {
          <form class="dv-card dv-card--r10 sy-form" (ngSubmit)="onSave()">
            <div class="dv-card__head">
              <span class="dv-card__title"
                >{{ editingId ? 'Edit' : 'Create' }} synonym group</span
              >
            </div>
            <div class="sy-form__body">
              <div>
                <label class="dv-field__label" for="sy-terms">terms (comma-separated)</label>
                <input
                  type="text"
                  id="sy-terms"
                  class="dv-input dv-input--mono"
                  [(ngModel)]="formTerms"
                  name="terms"
                  placeholder="invoice, bill, receipt"
                  required
                />
                <div class="dv-meta sy-hint">
                  every term in a group is treated as equivalent at query time — two
                  terms minimum
                </div>
              </div>

              <div class="sy-switch">
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

              <div class="sy-actions">
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
          <div class="sy-list">
            @for (synonym of synonyms(); track synonym.id) {
              <div class="dv-card dv-card--r9 sy-row">
                <span class="sy-terms">
                  @for (term of synonym.terms; track term; let last = $last) {
                    <span class="sy-term">{{ term }}</span>
                    @if (!last) {
                      <span class="sy-swap" aria-hidden="true">⇄</span>
                    }
                  }
                </span>

                <span class="dv-push"></span>
                @if (!synonym.enabled) {
                  <span class="dv-chip dv-chip--warn dv-chip--upper">disabled</span>
                }
                <button
                  type="button"
                  class="dv-toggle"
                  [class.is-on]="synonym.enabled"
                  role="switch"
                  [attr.aria-checked]="synonym.enabled"
                  aria-label="Toggle enabled"
                  (click)="toggleEnabled(synonym)"
                ></button>
                <button type="button" class="sy-action" (click)="onEdit(synonym)">edit</button>
                <button
                  type="button"
                  class="sy-action sy-action--danger"
                  title="Delete"
                  aria-label="Delete synonym group"
                  (click)="onDelete(synonym)"
                >
                  ✕
                </button>
              </div>
            } @empty {
              <div class="dv-empty">
                No synonym groups defined. Create one to improve search recall.
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

      .sy-head {
        align-items: center;
      }

      .sy-form {
        margin-bottom: 18px;

        &__body {
          padding: 16px 18px;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
      }

      .sy-hint {
        margin-top: 6px;
        line-height: 1.45;
      }

      .sy-switch {
        display: flex;
        align-items: center;
        gap: 9px;
        font-size: 13px;
        color: var(--muted);
      }

      .sy-actions {
        display: flex;
        gap: 8px;
      }

      .sy-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .sy-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        font: 400 12.5px #{$mono};
      }

      .sy-terms {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        min-width: 0;
      }

      .sy-term {
        color: var(--text);
      }

      .sy-swap {
        color: var(--accent-text);
      }

      .sy-action {
        background: none;
        border: none;
        padding: 0 2px;
        font: 400 11px #{$mono};
        color: var(--faint);
        cursor: pointer;

        &:hover {
          color: var(--text);
        }

        &--danger:hover {
          color: var(--danger);
        }
      }
    `,
  ],
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
