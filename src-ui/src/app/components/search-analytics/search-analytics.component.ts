import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchAnalytics } from '../../models/analytics.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-search-analytics',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-section sa-head">
          <span class="dv-eyebrow">range</span>
          @for (d of ranges; track d) {
            <button
              type="button"
              class="dv-token"
              [class.is-active]="selectedDays() === d"
              (click)="setDays(d)"
            >
              {{ d }}d
            </button>
          }
        </div>

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <span class="dv-sr">Loading…</span>
          </div>
        } @else if (analytics()) {
          <div class="sa-stats">
            <div class="dv-stat dv-stat--sm">
              <div class="dv-stat__label">queries / {{ selectedDays() }}d</div>
              <div class="dv-stat__row">
                <span class="dv-stat__value">{{ analytics()!.total_searches | number }}</span>
              </div>
            </div>
            <div class="dv-stat dv-stat--sm">
              <div class="dv-stat__label">click-through</div>
              <div class="dv-stat__row">
                <span
                  class="dv-stat__value"
                  [class.dv-ok]="analytics()!.click_through_rate >= 0.5"
                  [class.dv-warn]="
                    analytics()!.click_through_rate >= 0.2 &&
                    analytics()!.click_through_rate < 0.5
                  "
                  [class.dv-danger]="analytics()!.click_through_rate < 0.2"
                >
                  {{ analytics()!.click_through_rate * 100 | number : '1.1-1' }}%
                </span>
                <span class="dv-stat__delta dv-faint">of searches with clicks</span>
              </div>
            </div>
            <div class="dv-stat dv-stat--sm">
              <div class="dv-stat__label">avg click position</div>
              <div class="dv-stat__row">
                <span class="dv-stat__value">{{
                  analytics()!.avg_click_position | number : '1.1-1'
                }}</span>
                <span class="dv-stat__delta dv-faint">lower is better</span>
              </div>
            </div>
          </div>

          <div class="dv-section sa-section">
            <span class="dv-card__title">Top queries</span>
          </div>

          <div class="dv-thead dv-grid" style="--dv-cols: minmax(0,1fr) 90px 110px">
            <span>top query</span>
            <span class="dv-num">count</span>
            <span class="dv-num">avg results</span>
          </div>

          @for (q of analytics()!.top_queries; track q.query) {
            <div
              class="dv-row dv-row--static dv-grid"
              style="--dv-cols: minmax(0,1fr) 90px 110px"
            >
              <span class="dv-mono dv-clip sa-query">{{ q.query }}</span>
              <span class="dv-mono dv-num dv-muted">{{ q.count }}</span>
              <span class="dv-mono dv-num dv-faint">{{ q.avg_results | number : '1.0-0' }}</span>
            </div>
          } @empty {
            <div class="dv-empty">No query data available.</div>
          }

          <div class="dv-section sa-section">
            <span class="dv-card__title">Zero-result queries</span>
            <span class="dv-chip dv-chip--danger dv-chip--upper">needs attention</span>
          </div>

          <div class="dv-thead dv-grid" style="--dv-cols: minmax(0,1fr) 90px 130px">
            <span>query</span>
            <span class="dv-num">count</span>
            <span class="dv-num">action</span>
          </div>

          @for (q of analytics()!.zero_result_queries; track q.query) {
            <div
              class="dv-row dv-row--static dv-grid"
              style="--dv-cols: minmax(0,1fr) 90px 130px"
            >
              <span class="dv-mono dv-clip sa-query">{{ q.query }}</span>
              <span class="dv-mono dv-num dv-danger">{{ q.count }}</span>
              <span class="dv-num">
                <a
                  class="sa-action"
                  routerLink="/curations"
                  [queryParams]="{ query: q.query }"
                  title="Create curation for this query"
                  >📌 curate</a
                >
              </span>
            </div>
          } @empty {
            <div class="dv-empty">No zero-result queries.</div>
          }
        } @else {
          <div class="dv-empty">No analytics available.</div>
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

      .sa-head {
        align-items: center;
        gap: 8px;
      }

      .sa-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
      }

      .sa-section {
        gap: 9px;
        align-items: center;
      }

      .sa-query {
        font-size: 13px;
      }

      .sa-action {
        font: 400 11px #{$mono};
        color: var(--accent-text);

        &:hover {
          color: var(--text);
        }
      }
    `,
  ],
})
export class SearchAnalyticsComponent implements OnInit {
  analytics = signal<SearchAnalytics | null>(null);
  loading = signal(true);
  selectedDays = signal(30);
  /** Selectable look-back windows, in days. */
  readonly ranges = [7, 30, 90];

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
