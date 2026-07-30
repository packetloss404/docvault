import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { LegalHoldService } from '../../services/legal-hold.service';
import { LegalHold } from '../../models/legal-hold.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-legal-hold-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './legal-hold-dashboard.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <!-- Stats -->
        <div class="lh-stats">
          <div class="dv-stat dv-stat--sm">
            <div class="dv-stat__label">active holds</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value dv-danger">{{ activeCount() }}</span>
            </div>
          </div>
          <div class="dv-stat dv-stat--sm">
            <div class="dv-stat__label">documents held</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value">{{ totalDocumentsHeld() }}</span>
            </div>
          </div>
          <div class="dv-stat dv-stat--sm">
            <div class="dv-stat__label">draft holds</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value dv-muted">{{ draftCount() }}</span>
            </div>
          </div>
          <div class="dv-stat dv-stat--sm">
            <div class="dv-stat__label">released</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value dv-ok">{{ releasedCount() }}</span>
            </div>
          </div>
        </div>

        <div class="dv-section lh-section">
          <span class="dv-eyebrow">legal holds</span>
          <select
            class="dv-select lh-filter dv-push"
            aria-label="Filter by status"
            [ngModel]="statusFilter()"
            (ngModelChange)="onStatusFilterChange($event)"
          >
            <option value="">all statuses</option>
            <option value="draft">draft</option>
            <option value="active">active</option>
            <option value="released">released</option>
          </select>
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--md"
            (click)="showCreateForm = true"
          >
            + New hold
          </button>
        </div>

        <!-- Create form -->
        @if (showCreateForm) {
          <div class="dv-card dv-card--pad lh-form">
            <div class="dv-card__title lh-form__title">Create legal hold</div>

            <div class="lh-grid">
              <label class="lh-field">
                <span class="dv-field__label">name</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  placeholder="Hold name"
                  [(ngModel)]="newHold.name"
                />
              </label>
              <label class="lh-field">
                <span class="dv-field__label">matter number</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7 dv-mono"
                  placeholder="CASE-2024-001"
                  [(ngModel)]="newHold.matter_number"
                />
              </label>
              <label class="lh-field lh-field--full">
                <span class="dv-field__label">description</span>
                <textarea
                  class="dv-input dv-input--r7"
                  rows="3"
                  placeholder="Description of the legal hold…"
                  [(ngModel)]="newHold.description"
                ></textarea>
              </label>
            </div>

            <div class="lh-form__actions">
              <button type="button" class="dv-btn dv-btn--primary dv-btn--md" (click)="createHold()">
                Create hold
              </button>
              <button
                type="button"
                class="dv-btn dv-btn--ghost dv-btn--md"
                (click)="showCreateForm = false"
              >
                Cancel
              </button>
            </div>
          </div>
        }

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (filteredHolds().length === 0) {
          <div class="dv-empty">No legal holds found.</div>
        } @else {
          <div class="lh-list">
            @for (hold of filteredHolds(); track hold.id) {
              <div class="dv-card dv-card--r10 lh-card">
                <div class="lh-card__head">
                  <a class="lh-card__name dv-clip" [routerLink]="['/legal-holds', hold.id]">{{
                    hold.name
                  }}</a>
                  <span class="dv-chip dv-chip--upper" [ngClass]="getStatusBadgeClass(hold.status)">
                    {{ formatStatus(hold.status) }}
                  </span>
                  <span class="dv-chip dv-chip--well">{{ hold.matter_number }}</span>
                  <span class="dv-meta dv-push">{{ sinceLabel(hold) }}</span>
                </div>

                <div class="lh-card__stats">
                  <span>{{ hold.document_count }} docs preserved</span>
                  <span>custodians: {{ hold.custodian_count }}</span>
                  <span>{{ hold.criteria_count }} criteria</span>
                </div>

                @if (hold.description) {
                  <div class="lh-card__note">{{ hold.description }}</div>
                }
                @if (hold.status === 'active') {
                  <div class="lh-card__note dv-muted">
                    mutations blocked with HTTP 409 while active
                  </div>
                }
                @if (hold.status === 'released' && hold.release_reason) {
                  <div class="lh-card__note dv-muted">released: {{ hold.release_reason }}</div>
                }

                <div class="lh-card__foot">
                  <a class="dv-rowaction dv-rowaction--accent" [routerLink]="['/legal-holds', hold.id]">details →</a>
                  @if (hold.status === 'draft') {
                    <button
                      type="button"
                      class="dv-btn dv-btn--danger dv-btn--sm dv-push"
                      (click)="activateHold(hold)"
                    >
                      Activate
                    </button>
                  }
                  @if (hold.status === 'active') {
                    <button
                      type="button"
                      class="dv-btn dv-btn--ghost dv-btn--sm dv-push"
                      (click)="releaseHold(hold)"
                    >
                      Release
                    </button>
                  }
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class LegalHoldDashboardComponent implements OnInit {
  holds = signal<LegalHold[]>([]);
  loading = signal(false);
  statusFilter = signal('');
  showCreateForm = false;

  newHold: Partial<LegalHold> = {
    name: '',
    matter_number: '',
    description: '',
  };

  constructor(private legalHoldService: LegalHoldService) {}

  ngOnInit(): void {
    this.loadHolds();
  }

  loadHolds(): void {
    this.loading.set(true);
    const params: Record<string, string> = {};
    const status = this.statusFilter();
    if (status) {
      params['status'] = status;
    }
    this.legalHoldService.getHolds(params).subscribe({
      next: (data) => {
        this.holds.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  filteredHolds(): LegalHold[] {
    return this.holds();
  }

  activeCount(): number {
    return this.holds().filter((h) => h.status === 'active').length;
  }

  draftCount(): number {
    return this.holds().filter((h) => h.status === 'draft').length;
  }

  releasedCount(): number {
    return this.holds().filter((h) => h.status === 'released').length;
  }

  totalDocumentsHeld(): number {
    return this.holds()
      .filter((h) => h.status === 'active')
      .reduce((sum, h) => sum + h.document_count, 0);
  }

  onStatusFilterChange(value: string): void {
    this.statusFilter.set(value);
    this.loadHolds();
  }

  /** Console status chip modifier: an active hold is the dangerous state. */
  getStatusBadgeClass(status: LegalHold['status']): string {
    switch (status) {
      case 'active':
        return 'dv-chip--danger';
      case 'draft':
        return 'dv-chip--accent';
      default:
        return '';
    }
  }

  /** Mono clock readout: the date that defines the hold's current state. */
  sinceLabel(hold: LegalHold): string {
    if (hold.released_at) return `released ${this.formatDate(hold.released_at)}`;
    if (hold.activated_at) return `since ${this.formatDate(hold.activated_at)}`;
    return `created ${this.formatDate(hold.created_at)}`;
  }

  formatStatus(status: string): string {
    return status
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  createHold(): void {
    this.legalHoldService.createHold(this.newHold).subscribe({
      next: () => {
        this.showCreateForm = false;
        this.newHold = { name: '', matter_number: '', description: '' };
        this.loadHolds();
      },
    });
  }

  activateHold(hold: LegalHold): void {
    if (!confirm(`Activate legal hold "${hold.name}"? This will freeze all matching documents.`)) {
      return;
    }
    this.legalHoldService.activateHold(hold.id).subscribe({
      next: () => this.loadHolds(),
    });
  }

  releaseHold(hold: LegalHold): void {
    const reason = prompt(`Reason for releasing hold "${hold.name}":`);
    if (reason === null) return;
    this.legalHoldService.releaseHold(hold.id, reason).subscribe({
      next: () => this.loadHolds(),
    });
  }
}
