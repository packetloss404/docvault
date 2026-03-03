import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PortalConfig, PortalSubmission } from '../../models/portal.model';

@Component({
  selector: 'app-submission-review',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="container-fluid">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h4 class="mb-0"><i class="bi bi-check2-square me-2"></i>Submission Review Queue</h4>
      </div>

      <!-- Filters -->
      <div class="card mb-3">
        <div class="card-body py-2">
          <div class="row g-2 align-items-end">
            <div class="col-md-4">
              <label class="form-label small mb-1">Portal</label>
              <select
                class="form-select form-select-sm"
                [ngModel]="filterPortal()"
                (ngModelChange)="filterPortal.set($event); loadSubmissions()"
              >
                <option [ngValue]="0">All Portals</option>
                @for (p of portals(); track p.id) {
                  <option [ngValue]="p.id">{{ p.name }}</option>
                }
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label small mb-1">Status</label>
              <select
                class="form-select form-select-sm"
                [ngModel]="filterStatus()"
                (ngModelChange)="filterStatus.set($event); loadSubmissions()"
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
            <div class="col-md-4 text-end">
              <button class="btn btn-outline-secondary btn-sm" (click)="loadSubmissions()">
                <i class="bi bi-arrow-clockwise me-1"></i>Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Submissions List -->
      @if (loading()) {
        <div class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      } @else if (submissions().length === 0) {
        <div class="text-center text-muted py-4">
          <i class="bi bi-inbox fs-1"></i>
          <p class="mt-2">No submissions match the current filters.</p>
        </div>
      } @else {
        <div class="table-responsive">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Submitter</th>
                <th>Portal</th>
                <th>Request</th>
                <th>Status</th>
                <th>Submitted</th>
                <th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (sub of submissions(); track sub.id) {
                <tr>
                  <td>
                    <i class="bi bi-file-earmark me-1"></i>{{ sub.original_filename }}
                  </td>
                  <td>
                    {{ sub.submitter_name || sub.submitter_email || 'Anonymous' }}
                    @if (sub.submitter_name && sub.submitter_email) {
                      <br /><small class="text-muted">{{ sub.submitter_email }}</small>
                    }
                  </td>
                  <td>{{ sub.portal_name }}</td>
                  <td>
                    @if (sub.request) {
                      <span class="badge bg-info text-dark">Request #{{ sub.request }}</span>
                    } @else {
                      <span class="text-muted">Direct upload</span>
                    }
                  </td>
                  <td>
                    <span class="badge" [ngClass]="getStatusBadgeClass(sub.status)">
                      {{ sub.status }}
                    </span>
                  </td>
                  <td>{{ sub.submitted_at | date: 'short' }}</td>
                  <td class="text-end">
                    @if (sub.status === 'pending') {
                      <button
                        class="btn btn-success btn-sm me-1"
                        (click)="approveSubmission(sub)"
                        title="Approve"
                      >
                        <i class="bi bi-check-lg"></i>
                      </button>
                      <button
                        class="btn btn-danger btn-sm"
                        (click)="startReject(sub)"
                        title="Reject"
                      >
                        <i class="bi bi-x-lg"></i>
                      </button>
                    } @else if (sub.status === 'approved' && sub.ingested_document) {
                      <a
                        [routerLink]="['/documents', sub.ingested_document]"
                        class="btn btn-outline-primary btn-sm"
                        title="View ingested document"
                      >
                        <i class="bi bi-file-earmark-check me-1"></i>Document
                      </a>
                    } @else {
                      <span class="text-muted small">{{ sub.review_notes || '--' }}</span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      <!-- Reject Modal -->
      @if (rejectingSubmission()) {
        <div class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.5);">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">Reject Submission</h5>
                <button type="button" class="btn-close" (click)="rejectingSubmission.set(null)"></button>
              </div>
              <div class="modal-body">
                <p>
                  Rejecting: <strong>{{ rejectingSubmission()!.original_filename }}</strong>
                </p>
                <label class="form-label">Rejection Notes</label>
                <textarea
                  class="form-control"
                  rows="3"
                  [ngModel]="rejectNotes()"
                  (ngModelChange)="rejectNotes.set($event)"
                  placeholder="Reason for rejection..."
                ></textarea>
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary btn-sm" (click)="rejectingSubmission.set(null)">Cancel</button>
                <button class="btn btn-danger btn-sm" (click)="confirmReject()">
                  <i class="bi bi-x-lg me-1"></i>Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      }
    </div>
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

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending':
        return 'bg-warning text-dark';
      case 'approved':
        return 'bg-success';
      case 'rejected':
        return 'bg-danger';
      default:
        return 'bg-secondary';
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
