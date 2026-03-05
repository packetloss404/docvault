import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import {
  ZoneOCRResult,
  ZoneOCRTemplate,
} from '../../models/zone-ocr.model';

@Component({
  selector: 'app-zone-ocr-review',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>OCR Review Queue</h2>
      @if (selectedIds().size > 0) {
        <button class="btn btn-success" (click)="bulkAccept()">
          <i class="bi bi-check-all me-1"></i>Accept Selected ({{ selectedIds().size }})
        </button>
      }
    </div>

    <!-- Filters -->
    <div class="card mb-4">
      <div class="card-body">
        <div class="row g-3 align-items-end">
          <div class="col-md-3">
            <label class="form-label">Template</label>
            <select class="form-select" [(ngModel)]="filterTemplate" (ngModelChange)="loadResults()">
              <option [ngValue]="null">All Templates</option>
              @for (t of templates(); track t.id) {
                <option [ngValue]="t.id">{{ t.name }}</option>
              }
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label">Min Confidence</label>
            <input
              type="number"
              class="form-control"
              [(ngModel)]="filterMinConfidence"
              (ngModelChange)="loadResults()"
              min="0"
              max="1"
              step="0.05"
              placeholder="0.0"
            />
          </div>
          <div class="col-md-2">
            <label class="form-label">Max Confidence</label>
            <input
              type="number"
              class="form-control"
              [(ngModel)]="filterMaxConfidence"
              (ngModelChange)="loadResults()"
              min="0"
              max="1"
              step="0.05"
              placeholder="1.0"
            />
          </div>
          <div class="col-md-2">
            <div class="form-check mt-4">
              <input
                class="form-check-input"
                type="checkbox"
                [(ngModel)]="filterUnreviewedOnly"
                (ngModelChange)="loadResults()"
                id="unreviewedCheck"
              />
              <label class="form-check-label" for="unreviewedCheck">Unreviewed only</label>
            </div>
          </div>
          <div class="col-md-3 text-end">
            <span class="text-muted">{{ totalCount() }} results</span>
          </div>
        </div>
      </div>
    </div>

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
              <th style="width: 40px;">
                <input
                  class="form-check-input"
                  type="checkbox"
                  [checked]="allSelected()"
                  (change)="toggleSelectAll()"
                />
              </th>
              <th>Document</th>
              <th>Template</th>
              <th>Field</th>
              <th>Extracted Value</th>
              <th>Confidence</th>
              <th>Corrected Value</th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (result of results(); track result.id) {
              <tr [class.table-success]="result.reviewed">
                <td>
                  <input
                    class="form-check-input"
                    type="checkbox"
                    [checked]="selectedIds().has(result.id)"
                    (change)="toggleSelect(result.id)"
                  />
                </td>
                <td>
                  <a [routerLink]="['/documents', result.document]" class="text-decoration-none">
                    Doc #{{ result.document }}
                  </a>
                </td>
                <td>{{ result.template_name }}</td>
                <td class="fw-semibold">{{ result.field_name }}</td>
                <td><code>{{ result.extracted_value }}</code></td>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <div class="progress flex-grow-1" style="height: 8px; min-width: 60px;">
                      <div
                        class="progress-bar"
                        [class.bg-success]="result.confidence >= 0.8"
                        [class.bg-warning]="result.confidence >= 0.5 && result.confidence < 0.8"
                        [class.bg-danger]="result.confidence < 0.5"
                        [style.width.%]="result.confidence * 100"
                      ></div>
                    </div>
                    <span class="small fw-semibold" [class.text-success]="result.confidence >= 0.8" [class.text-warning]="result.confidence >= 0.5 && result.confidence < 0.8" [class.text-danger]="result.confidence < 0.5">
                      {{ (result.confidence * 100).toFixed(0) }}%
                    </span>
                  </div>
                </td>
                <td>
                  <input
                    type="text"
                    class="form-control form-control-sm"
                    [ngModel]="getCorrectionValue(result)"
                    (ngModelChange)="corrections[result.id] = $event"
                    (blur)="onCorrectionBlur(result)"
                    placeholder="Enter correction..."
                    style="min-width: 150px;"
                  />
                </td>
                <td class="text-end">
                  @if (result.reviewed) {
                    <span class="badge bg-success">
                      <i class="bi bi-check-lg"></i> Reviewed
                    </span>
                  } @else {
                    <button
                      class="btn btn-sm btn-outline-success"
                      (click)="acceptResult(result)"
                      title="Accept"
                    >
                      <i class="bi bi-check-lg"></i> Accept
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="8" class="text-center text-muted py-4">
                  No OCR results matching the current filters.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      @if (totalCount() > pageSize) {
        <nav class="d-flex justify-content-center mt-3">
          <ul class="pagination">
            <li class="page-item" [class.disabled]="currentPage() === 1">
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
