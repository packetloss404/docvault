import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import {
  ZoneOCRResult,
  ZoneOCRTemplate,
} from '../../models/zone-ocr.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-zone-ocr-review',
  standalone: true,
  imports: [FormsModule, RouterLink, SubnavComponent],
  styleUrl: './zone-ocr-review.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-pagehead pagehead">
          <h1 class="dv-h1 dv-h1--sm">OCR review queue</h1>
          <span class="dv-ts">{{ totalCount() }} results</span>
        </div>

        <!-- Filters -->
        <div class="dv-card dv-card--pad filters">
          <div class="filter-grid">
            <div>
              <label class="dv-field__label" for="zr-template">template</label>
              <select
                id="zr-template"
                class="dv-select"
                [(ngModel)]="filterTemplate"
                (ngModelChange)="loadResults()"
              >
                <option [ngValue]="null">All templates</option>
                @for (t of templates(); track t.id) {
                  <option [ngValue]="t.id">{{ t.name }}</option>
                }
              </select>
            </div>

            <div>
              <label class="dv-field__label" for="zr-min">min confidence</label>
              <input
                id="zr-min"
                type="number"
                class="dv-input dv-input--mono"
                [(ngModel)]="filterMinConfidence"
                (ngModelChange)="loadResults()"
                min="0"
                max="1"
                step="0.05"
                placeholder="0.00"
              />
            </div>

            <div>
              <label class="dv-field__label" for="zr-max">max confidence</label>
              <input
                id="zr-max"
                type="number"
                class="dv-input dv-input--mono"
                [(ngModel)]="filterMaxConfidence"
                (ngModelChange)="loadResults()"
                min="0"
                max="1"
                step="0.05"
                placeholder="1.00"
              />
            </div>

            <div class="form-switch">
              <span class="dv-field__label">unreviewed only</span>
              <button
                type="button"
                class="dv-toggle"
                [class.is-on]="filterUnreviewedOnly"
                [attr.aria-pressed]="filterUnreviewedOnly"
                aria-label="Unreviewed only"
                (click)="filterUnreviewedOnly = !filterUnreviewedOnly; loadResults()"
              ></button>
            </div>
          </div>
        </div>

        @if (selectedIds().size > 0) {
          <div class="dv-bulkbar bulkbar">
            <span class="dv-bulkbar__count">{{ selectedIds().size }} selected</span>
            <button type="button" class="dv-bulkbar__action" (click)="bulkAccept()">
              ✓ Approve all
            </button>
            <button
              type="button"
              class="dv-bulkbar__action dv-push"
              (click)="clearSelection()"
            >
              ✕ Clear
            </button>
          </div>
        }

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <div class="load-label">Loading extraction results…</div>
          </div>
        } @else {
          <div class="list">
            <div
              class="dv-thead dv-grid"
              style="--dv-cols: 26px 90px 1fr 1fr 1.2fr 130px 1.1fr 86px"
            >
              <button
                type="button"
                class="dv-check"
                [class.is-checked]="allSelected()"
                aria-label="Select all"
                (click)="toggleSelectAll()"
              >
                @if (allSelected()) {
                  ✓
                }
              </button>
              <span>document</span>
              <span>template</span>
              <span>field</span>
              <span>extracted</span>
              <span>confidence</span>
              <span>correction</span>
              <span></span>
            </div>

            @for (result of results(); track result.id) {
              <div
                class="dv-row dv-row--static dv-grid"
                [class.is-reviewed]="result.reviewed"
                style="--dv-cols: 26px 90px 1fr 1fr 1.2fr 130px 1.1fr 86px"
              >
                <button
                  type="button"
                  class="dv-check"
                  [class.is-checked]="selectedIds().has(result.id)"
                  [attr.aria-label]="'Select result ' + result.id"
                  (click)="toggleSelect(result.id)"
                >
                  @if (selectedIds().has(result.id)) {
                    ✓
                  }
                </button>

                <a class="doc-link" [routerLink]="['/documents', result.document]">
                  #{{ result.document }}
                </a>
                <span class="dv-muted dv-clip">{{ result.template_name }}</span>
                <span class="row-name dv-clip">{{ result.field_name }}</span>
                <span class="dv-meta dv-clip">{{ result.extracted_value || '—' }}</span>

                <span class="conf">
                  <span class="dv-bar dv-bar--micro">
                    <span
                      class="dv-bar__fill"
                      [class.dv-bar__fill--ok]="result.confidence >= 0.8"
                      [class.dv-bar__fill--warn]="
                        result.confidence >= 0.5 && result.confidence < 0.8
                      "
                      [class.dv-bar__fill--danger]="result.confidence < 0.5"
                      [style.width.%]="result.confidence * 100"
                    ></span>
                  </span>
                  <span
                    class="conf__pct"
                    [class.dv-ok]="result.confidence >= 0.8"
                    [class.dv-warn]="result.confidence >= 0.5 && result.confidence < 0.8"
                    [class.dv-danger]="result.confidence < 0.5"
                  >
                    {{ (result.confidence * 100).toFixed(0) }}%
                  </span>
                </span>

                <input
                  type="text"
                  class="dv-input dv-input--mono dv-input--r7 correction"
                  [ngModel]="getCorrectionValue(result)"
                  (ngModelChange)="corrections[result.id] = $event"
                  (blur)="onCorrectionBlur(result)"
                  placeholder="correction…"
                  [attr.aria-label]="'Correction for ' + result.field_name"
                />

                <span class="row-actions">
                  @if (result.reviewed) {
                    <span class="dv-chip dv-chip--ok dv-chip--upper">reviewed</span>
                  } @else {
                    <button type="button" class="row-action" (click)="acceptResult(result)">
                      accept
                    </button>
                  }
                </span>
              </div>
            } @empty {
              <div class="dv-empty">No OCR results matching the current filters.</div>
            }
          </div>

          @if (totalCount() > pageSize) {
            <div class="dv-pager">
              <span (click)="goToPage(currentPage() - 1)">‹ prev</span>
              @for (p of pageNumbers(); track p) {
                <span [class.is-current]="p === currentPage()" (click)="goToPage(p)">{{ p }}</span>
              }
              <span (click)="goToPage(currentPage() + 1)">next ›</span>
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class ZoneOcrReviewComponent implements OnInit {
  results = signal<ZoneOCRResult[]>([]);
  templates = signal<ZoneOCRTemplate[]>([]);
  loading = signal(true);
  totalCount = signal(0);
  currentPage = signal(1);
  selectedIds = signal(new Set<number>());

  filterTemplate: number | null = null;
  filterMinConfidence: number | null = null;
  filterMaxConfidence: number | null = null;
  filterUnreviewedOnly = true;

  corrections: Record<number, string> = {};
  pageSize = 25;

  constructor(private zoneOcrService: ZoneOCRService) {}

  ngOnInit(): void {
    this.loadTemplates();
    this.loadResults();
  }

  loadTemplates(): void {
    this.zoneOcrService.getTemplates().subscribe({
      next: (resp) => this.templates.set(resp.results),
    });
  }

  loadResults(): void {
    this.loading.set(true);
    const params: Record<string, unknown> = {
      page: this.currentPage(),
      page_size: this.pageSize,
    };
    if (this.filterTemplate !== null) params['template'] = this.filterTemplate;
    if (this.filterMinConfidence !== null) params['min_confidence'] = this.filterMinConfidence;
    if (this.filterMaxConfidence !== null) params['max_confidence'] = this.filterMaxConfidence;
    if (this.filterUnreviewedOnly) params['reviewed'] = false;

    this.zoneOcrService.getResults(params as Record<string, number | boolean>).subscribe({
      next: (resp) => {
        this.results.set(resp.results);
        this.totalCount.set(resp.count);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize);
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

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadResults();
  }

  allSelected(): boolean {
    const ids = this.selectedIds();
    return this.results().length > 0 && this.results().every((r) => ids.has(r.id));
  }

  toggleSelectAll(): void {
    if (this.allSelected()) {
      this.selectedIds.set(new Set());
    } else {
      this.selectedIds.set(new Set(this.results().map((r) => r.id)));
    }
  }

  clearSelection(): void {
    this.selectedIds.set(new Set());
  }

  toggleSelect(id: number): void {
    const ids = new Set(this.selectedIds());
    if (ids.has(id)) {
      ids.delete(id);
    } else {
      ids.add(id);
    }
    this.selectedIds.set(ids);
  }

  getCorrectionValue(result: ZoneOCRResult): string {
    const val = this.corrections[result.id];
    return val !== undefined ? val : result.corrected_value;
  }

  acceptResult(result: ZoneOCRResult): void {
    const corrected = this.corrections[result.id] ?? result.corrected_value ?? result.extracted_value;
    this.zoneOcrService
      .correctResult(result.id, { corrected_value: corrected, reviewed: true })
      .subscribe({
        next: (updated) => {
          this.results.update((list) =>
            list.map((r) => (r.id === updated.id ? updated : r)),
          );
        },
      });
  }

  onCorrectionBlur(result: ZoneOCRResult): void {
    const corrected = this.corrections[result.id];
    if (corrected !== undefined && corrected !== result.corrected_value) {
      this.zoneOcrService
        .correctResult(result.id, { corrected_value: corrected, reviewed: true })
        .subscribe({
          next: (updated) => {
            this.results.update((list) =>
              list.map((r) => (r.id === updated.id ? updated : r)),
            );
          },
        });
    }
  }

  bulkAccept(): void {
    const ids = Array.from(this.selectedIds());
    let completed = 0;
    for (const id of ids) {
      const result = this.results().find((r) => r.id === id);
      if (!result || result.reviewed) {
        completed++;
        continue;
      }
      const corrected = this.corrections[id] ?? result.corrected_value ?? result.extracted_value;
      this.zoneOcrService
        .correctResult(id, { corrected_value: corrected, reviewed: true })
        .subscribe({
          next: (updated) => {
            this.results.update((list) =>
              list.map((r) => (r.id === updated.id ? updated : r)),
            );
            completed++;
            if (completed === ids.length) {
              this.selectedIds.set(new Set());
            }
          },
        });
    }
  }
}
