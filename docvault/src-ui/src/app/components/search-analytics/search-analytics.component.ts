import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchAnalytics } from '../../models/analytics.model';

@Component({
  selector: 'app-search-analytics',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Search Analytics</h2>
      <div class="btn-group">
        <button
          class="btn btn-sm"
          [class.btn-primary]="selectedDays() === 7"
          [class.btn-outline-primary]="selectedDays() !== 7"
          (click)="setDays(7)"
        >
          7 days
        </button>
        <button
          class="btn btn-sm"
          [class.btn-primary]="selectedDays() === 30"
          [class.btn-outline-primary]="selectedDays() !== 30"
          (click)="setDays(30)"
        >
          30 days
        </button>
        <button
          class="btn btn-sm"
          [class.btn-primary]="selectedDays() === 90"
          [class.btn-outline-primary]="selectedDays() !== 90"
          (click)="setDays(90)"
        >
          90 days
        </button>
      </div>
    </div>

    @if (loading()) {
      <div class="text-center py-5">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (analytics()) {
      <!-- Summary Cards -->
      <div class="row g-4 mb-4">
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <div class="text-muted small mb-1">Total Searches</div>
              <div class="display-6 fw-bold text-primary">
                {{ analytics()!.total_searches | number }}
              </div>
              <div class="text-muted small">Last {{ selectedDays() }} days</div>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <div class="text-muted small mb-1">Avg Click Position</div>
              <div class="display-6 fw-bold text-info">
                {{ analytics()!.avg_click_position | number:'1.1-1' }}
              </div>
              <div class="text-muted small">Lower is better</div>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <div class="text-muted small mb-1">Click-Through Rate</div>
              <div class="display-6 fw-bold" [class.text-success]="analytics()!.click_through_rate >= 0.5" [class.text-warning]="analytics()!.click_through_rate >= 0.2 && analytics()!.click_through_rate < 0.5" [class.text-danger]="analytics()!.click_through_rate < 0.2">
                {{ (analytics()!.click_through_rate * 100) | number:'1.1-1' }}%
              </div>
              <div class="text-muted small">Of searches with clicks</div>
            </div>
          </div>
        </div>
      </div>

      <div class="row g-4">
        <!-- Top Queries -->
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">Top Queries</h5>
            </div>
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Query</th>
                    <th class="text-end">Count</th>
                    <th class="text-end">Avg Results</th>
                  </tr>
                </thead>
                <tbody>
                  @for (q of analytics()!.top_queries; track q.query; let i = $index) {
                    <tr>
                      <td class="text-muted">{{ i + 1 }}</td>
                      <td>
                        <code>{{ q.query }}</code>
                      </td>
                      <td class="text-end">
                        <span class="badge bg-primary">{{ q.count }}</span>
                      </td>
                      <td class="text-end text-muted">{{ q.avg_results | number:'1.0-0' }}</td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="4" class="text-center text-muted py-3">No query data available.</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Zero-Result Queries -->
        <div class="col-md-6">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0">Zero-Result Queries</h5>
              <span class="badge bg-danger">Needs Attention</span>
            </div>
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Query</th>
                    <th class="text-end">Count</th>
                    <th class="text-end">Action</th>
                  </tr>
                </thead>
                <tbody>
                  @for (q of analytics()!.zero_result_queries; track q.query; let i = $index) {
                    <tr>
                      <td class="text-muted">{{ i + 1 }}</td>
                      <td>
                        <code>{{ q.query }}</code>
                      </td>
                      <td class="text-end">
                        <span class="badge bg-danger">{{ q.count }}</span>
                      </td>
                      <td class="text-end">
                        <a
                          routerLink="/curations"
                          [queryParams]="{ query: q.query }"
                          class="btn btn-sm btn-outline-warning"
                          title="Create curation for this query"
                        >
                          <i class="bi bi-pin-angle me-1"></i>Create Curation
                        </a>
                      </td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="4" class="text-center text-muted py-3">No zero-result queries. Great!</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    }
  `,
})
export class SearchAnalyticsComponent implements OnInit {
  analytics = signal<SearchAnalytics | null>(null);
  loading = signal(true);
  selectedDays = signal(30);

  constructor(private analyticsService: AnalyticsService) {}

  ngOnInit(): void {
    this.loadAnalytics();
  }

  setDays(days: number): void {
    this.selectedDays.set(days);
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    this.loading.set(true);
    this.analyticsService.getAnalytics(this.selectedDays()).subscribe({
      next: (data) => {
        this.analytics.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
