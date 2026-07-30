import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { EsignatureService } from '../../services/esignature.service';
import { SignatureRequest, Signer } from '../../models/esignature.model';

@Component({
  selector: 'app-signature-requests',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  styleUrl: './signature-requests.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <div class="dv-pagehead">
          <h1 class="dv-h1 dv-h1--sm">Signature requests</h1>
          <select
            class="dv-select sr-filter dv-push"
            aria-label="Filter by status"
            [ngModel]="statusFilter()"
            (ngModelChange)="onStatusFilterChange($event)"
          >
            <option value="">all statuses</option>
            <option value="draft">draft</option>
            <option value="sent">sent</option>
            <option value="in_progress">in progress</option>
            <option value="completed">completed</option>
            <option value="cancelled">cancelled</option>
            <option value="expired">expired</option>
          </select>
          <a class="dv-btn dv-btn--primary" routerLink="/documents">+ New request</a>
        </div>

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (filteredRequests().length === 0) {
          <div class="dv-empty">No signature requests found.</div>
        } @else {
          <div class="sr-list">
            @for (req of filteredRequests(); track req.id) {
              <div class="dv-card dv-card--r10 dv-card--hover sr-card">
                <div class="sr-card__head">
                  <a class="sr-card__title" [routerLink]="['/signature-requests', req.id]">{{
                    req.title
                  }}</a>
                  <span class="dv-chip dv-chip--upper" [ngClass]="getStatusBadgeClass(req.status)">
                    {{ formatStatus(req.status) }}
                  </span>
                  <a class="dv-meta sr-card__doc" [routerLink]="['/documents', req.document]"
                    >doc #{{ req.document }}</a
                  >
                  <span class="dv-meta dv-push">{{ dueLabel(req) }}</span>
                </div>

                <div class="sr-card__foot">
                  <div class="dv-chain sr-chain">
                    @for (signer of req.signers; track signer.id) {
                      <span class="sr-signer">
                        <span
                          class="dv-avatar dv-avatar--sm"
                          [class.dv-avatar--signed]="signer.status === 'signed'"
                          >{{ initials(signer.name) }}</span
                        >
                        <span class="sr-signer__name">{{ signer.name }}</span>
                        <span class="dv-meta" [ngClass]="signerStateClass(req, signer)">{{
                          signerState(req, signer)
                        }}</span>
                      </span>
                      @if (!$last) {
                        <span class="dv-chain__arrow" aria-hidden="true">→</span>
                      }
                    }
                    @if (req.signers.length === 0) {
                      <span class="dv-meta">no signers</span>
                    }
                  </div>

                  <span class="dv-meta sr-mode">{{ req.signing_order }}</span>

                  @if (req.status === 'sent' || req.status === 'in_progress') {
                    <button
                      type="button"
                      class="dv-btn dv-btn--sm dv-btn--warn"
                      title="Remind signers"
                      (click)="remind(req)"
                    >
                      remind
                    </button>
                    <button
                      type="button"
                      class="dv-btn dv-btn--sm dv-btn--danger"
                      title="Cancel request"
                      (click)="cancel(req)"
                    >
                      cancel
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
export class SignatureRequestsComponent implements OnInit {
  requests = signal<SignatureRequest[]>([]);
  loading = signal(false);
  statusFilter = signal('');

  constructor(private esignatureService: EsignatureService) {}

  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests(): void {
    this.loading.set(true);
    const params: Record<string, string> = {};
    const status = this.statusFilter();
    if (status) {
      params['status'] = status;
    }
    this.esignatureService.getRequests(params).subscribe({
      next: (data) => {
        this.requests.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  filteredRequests(): SignatureRequest[] {
    return this.requests();
  }

  onStatusFilterChange(value: string): void {
    this.statusFilter.set(value);
    this.loadRequests();
  }

  /** Console status chip modifier for a request status. */
  getStatusBadgeClass(status: SignatureRequest['status']): string {
    switch (status) {
      case 'sent':
        return 'dv-chip--accent';
      case 'in_progress':
        return 'dv-chip--warn';
      case 'completed':
        return 'dv-chip--ok';
      case 'cancelled':
      case 'expired':
        return 'dv-chip--danger';
      default:
        return '';
    }
  }

  /** Lowercase two-letter monogram, as the signer chain in the design uses. */
  initials(name: string): string {
    const parts = (name || '').trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return '··';
    if (parts.length === 1) return parts[0].slice(0, 2).toLowerCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toLowerCase();
  }

  /**
   * Chain state word. For a sequential request only the first outstanding
   * signer is actually waiting; the rest are queued behind them.
   */
  signerState(req: SignatureRequest, signer: Signer): string {
    if (signer.status === 'signed') return 'signed';
    if (signer.status === 'declined') return 'declined';
    if (signer.status === 'viewed') return 'viewed';
    if (req.status === 'draft') return 'queued';
    if (req.signing_order === 'parallel') return 'waiting';
    const nextUp = req.signers
      .filter((s) => s.status !== 'signed' && s.status !== 'declined')
      .sort((a, b) => a.order - b.order)[0];
    return nextUp && nextUp.id === signer.id ? 'waiting' : 'queued';
  }

  signerStateClass(req: SignatureRequest, signer: Signer): string {
    switch (this.signerState(req, signer)) {
      case 'signed':
        return 'dv-ok';
      case 'declined':
        return 'dv-danger';
      case 'viewed':
      case 'waiting':
        return 'dv-warn';
      default:
        return 'dv-faint';
    }
  }

  /** Mono deadline readout: what matters most about this request's clock. */
  dueLabel(req: SignatureRequest): string {
    if (req.completed_at) return `completed ${this.formatDate(req.completed_at)}`;
    if (req.expiration) {
      return req.status === 'expired'
        ? `expired ${this.formatDate(req.expiration)}`
        : `expires ${this.formatDate(req.expiration)}`;
    }
    return `created ${this.formatDate(req.created_at)}`;
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

  cancel(req: SignatureRequest): void {
    if (!confirm(`Cancel signature request "${req.title}"?`)) return;
    this.esignatureService.cancelRequest(req.id).subscribe({
      next: () => this.loadRequests(),
    });
  }

  remind(req: SignatureRequest): void {
    this.esignatureService.remindSigners(req.id).subscribe({
      next: () => alert('Reminder sent to pending signers.'),
    });
  }
}
