import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PortalConfig, PortalSubmission } from '../../models/portal.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-submission-review',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './submission-review.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="sv-filters">
          <select
            class="dv-select sv-select"
            aria-label="Filter by portal"
            [ngModel]="filterPortal()"
            (ngModelChange)="filterPortal.set($event); loadSubmissions()"
          >
            <option [ngValue]="0">all portals</option>
            @for (p of portals(); track p.id) {
              <option [ngValue]="p.id">{{ p.name }}</option>
            }
          </select>

          <select
            class="dv-select sv-select"
            aria-label="Filter by status"
            [ngModel]="filterStatus()"
            (ngModelChange)="filterStatus.set($event); loadSubmissions()"
          >
            <option value="">all statuses</option>
            <option value="pending">pending</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>

          <button
            type="button"
            class="dv-btn dv-btn--ghost dv-btn--md dv-push"
            (click)="loadSubmissions()"
          >
            ↻ Refresh
          </button>
        </div>

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (submissions().length === 0) {
          <div class="dv-empty">No submissions match the current filters.</div>
        } @else {
          <div class="sv-list">
            @for (sub of submissions(); track sub.id) {
              <div class="dv-card dv-card--r10 sv-row">
                <span class="dv-thumb" aria-hidden="true"></span>

                <div class="sv-row__main">
                  <div class="sv-row__file dv-clip">{{ sub.original_filename }}</div>
                  <div class="dv-meta sv-row__meta">
                    via {{ sub.portal_name }} · by
                    {{ sub.submitter_name || sub.submitter_email || 'anonymous' }}
                    @if (sub.submitter_name && sub.submitter_email) {
                      ({{ sub.submitter_email }})
                    }
                    @if (sub.request) {
                      · request #{{ sub.request }}
                    } @else {
                      · direct upload
                    }
                  </div>
                </div>

                <span class="dv-chip dv-chip--upper" [ngClass]="getStatusBadgeClass(sub.status)">{{
                  sub.status
                }}</span>

                <span class="dv-meta sv-row__when">{{ sub.submitted_at | date: 'short' }}</span>

                @if (sub.status === 'pending') {
                  <button
                    type="button"
                    class="dv-btn dv-btn--primary dv-btn--sm"
                    (click)="approveSubmission(sub)"
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    class="dv-btn dv-btn--danger dv-btn--sm"
                    (click)="startReject(sub)"
                  >
                    Reject
                  </button>
                } @else if (sub.status === 'approved' && sub.ingested_document) {
                  <a
                    class="dv-btn dv-btn--ghost dv-btn--sm"
                    [routerLink]="['/documents', sub.ingested_document]"
                    title="View ingested document"
                    >Document</a
                  >
                } @else {
                  <span class="dv-meta sv-row__notes dv-clip" [title]="sub.review_notes">{{
                    sub.review_notes || '—'
                  }}</span>
                }
              </div>
            }
          </div>
        }
      </div>
    </div>

    <!-- Reject dialog -->
    @if (rejectingSubmission()) {
      <div class="dv-overlay" (click)="rejectingSubmission.set(null)">
        <div
          class="dv-modal"
          role="dialog"
          aria-modal="true"
          aria-label="Reject submission"
          (click)="$event.stopPropagation()"
        >
          <div class="dv-modal__head">
            <span>Reject submission</span>
            <button
              type="button"
              class="dv-modal__close"
              aria-label="Close"
              (click)="rejectingSubmission.set(null)"
            >
              ✕
            </button>
          </div>

          <div class="dv-modal__body sv-modal__body">
            <div class="dv-meta">{{ rejectingSubmission()!.original_filename }}</div>
            <label>
              <span class="dv-field__label">rejection notes</span>
              <textarea
                class="dv-input dv-input--r7"
                rows="3"
                placeholder="Reason for rejection…"
                [ngModel]="rejectNotes()"
                (ngModelChange)="rejectNotes.set($event)"
              ></textarea>
            </label>
          </div>

          <div class="dv-modal__foot">
            <button
              type="button"
              class="dv-btn dv-btn--ghost dv-btn--md dv-push"
              (click)="rejectingSubmission.set(null)"
            >
              Cancel
            </button>
            <button type="button" class="dv-btn dv-btn--danger dv-btn--md" (click)="confirmReject()">
              Reject
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class SubmissionReviewComponent implements OnInit {
  submissions = signal<PortalSubmission[]>([]);
  portals = signal<PortalConfig[]>([]);
  loading = signal(true);

  filterPortal = signal<number>(0);
  filterStatus = signal('');

  rejectingSubmission = signal<PortalSubmission | null>(null);
  rejectNotes = signal('');

  constructor(private portalService: PortalService) {}

  ngOnInit(): void {
    this.loadPortals();
    this.loadSubmissions();
  }

  loadPortals(): void {
    this.portalService.getPortals().subscribe({
      next: (resp) => this.portals.set(resp.results),
    });
  }

  loadSubmissions(): void {
    this.loading.set(true);
    const params: { portal?: number; status?: string } = {};
    if (this.filterPortal()) params.portal = this.filterPortal();
    if (this.filterStatus()) params.status = this.filterStatus();

    this.portalService.getSubmissions(params).subscribe({
      next: (resp) => {
        this.submissions.set(resp.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  /** Console status chip modifier for a submission status. */
  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending':
        return 'dv-chip--warn';
      case 'approved':
        return 'dv-chip--ok';
      case 'rejected':
        return 'dv-chip--danger';
      default:
        return '';
    }
  }

  approveSubmission(sub: PortalSubmission): void {
    if (!confirm(`Approve "${sub.original_filename}"?`)) return;
    this.portalService.reviewSubmission(sub.id, { status: 'approved' }).subscribe({
      next: () => this.loadSubmissions(),
    });
  }

  startReject(sub: PortalSubmission): void {
    this.rejectingSubmission.set(sub);
    this.rejectNotes.set('');
  }

  confirmReject(): void {
    const sub = this.rejectingSubmission();
    if (!sub) return;
    this.portalService
      .reviewSubmission(sub.id, {
        status: 'rejected',
        review_notes: this.rejectNotes(),
      })
      .subscribe({
        next: () => {
          this.rejectingSubmission.set(null);
          this.loadSubmissions();
        },
      });
  }
}
