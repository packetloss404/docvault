import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { EsignatureService } from '../../services/esignature.service';
import {
  SignatureRequest,
  SignatureAuditEvent,
} from '../../models/esignature.model';

@Component({
  selector: 'app-signature-request-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    @if (loading()) {
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (errorMsg()) {
      <div class="alert alert-danger">{{ errorMsg() }}</div>
    } @else if (request()) {
      <!-- Header -->
      <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
          <a routerLink="/signature-requests" class="text-decoration-none small">
            <i class="bi bi-arrow-left me-1"></i>Back to Requests
          </a>
          <h3 class="mt-1 mb-0">{{ request()!.title }}</h3>
        </div>
        <div class="btn-group">
          @if (request()!.status === 'draft') {
            <button class="btn btn-primary" (click)="send()">
              <i class="bi bi-send me-1"></i>Send
            </button>
          }
          @if (request()!.status === 'sent' || request()!.status === 'in_progress') {
            <button class="btn btn-outline-warning" (click)="remind()">
              <i class="bi bi-bell me-1"></i>Remind
            </button>
            <button class="btn btn-outline-danger" (click)="cancel()">
              <i class="bi bi-x-circle me-1"></i>Cancel
            </button>
          }
          @if (request()!.status === 'completed') {
            <button class="btn btn-outline-success" (click)="downloadCertificate()">
              <i class="bi bi-download me-1"></i>Download Certificate
            </button>
          }
        </div>
      </div>

      <!-- Details Card -->
      <div class="card mb-4">
        <div class="card-header">Request Details</div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-6">
              <dl>
                <dt>Status</dt>
                <dd>
                  <span class="badge" [ngClass]="getStatusBadgeClass(request()!.status)">
                    {{ formatStatus(request()!.status) }}
                  </span>
                </dd>
                <dt>Signing Order</dt>
                <dd>{{ request()!.signing_order === 'sequential' ? 'Sequential' : 'Parallel' }}</dd>
              </dl>
            </div>
            <div class="col-md-6">
              <dl>
                <dt>Expiration</dt>
                <dd>{{ request()!.expiration ? formatDate(request()!.expiration!) : 'None' }}</dd>
                <dt>Completed At</dt>
                <dd>{{ request()!.completed_at ? formatDate(request()!.completed_at!) : '--' }}</dd>
              </dl>
            </div>
          </div>
          @if (request()!.message) {
            <div>
              <dt>Message</dt>
              <dd class="text-muted" style="white-space: pre-wrap;">{{ request()!.message }}</dd>
            </div>
          }
        </div>
      </div>

      <!-- Signers Table -->
      <div class="card mb-4">
        <div class="card-header">Signers</div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Signed At</th>
                </tr>
              </thead>
              <tbody>
                @for (signer of request()!.signers; track signer.id) {
                  <tr>
                    <td>{{ signer.order }}</td>
                    <td>{{ signer.name }}</td>
                    <td>{{ signer.email }}</td>
                    <td>{{ signer.role }}</td>
                    <td>
                      <span class="badge" [ngClass]="getSignerStatusClass(signer.status)">
                        {{ formatStatus(signer.status) }}
                      </span>
                    </td>
                    <td>{{ signer.signed_at ? formatDate(signer.signed_at) : '--' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Audit Trail -->
      <div class="card">
        <div class="card-header">
          <i class="bi bi-clock-history me-1"></i>Audit Trail
        </div>
        <div class="card-body">
          @if (auditEvents().length === 0) {
            <p class="text-muted mb-0">No audit events yet.</p>
          } @else {
            <ul class="list-unstyled mb-0">
              @for (event of auditEvents(); track event.id) {
                <li class="d-flex mb-3">
                  <div class="me-3 text-muted" style="min-width: 140px; font-size: 0.85em;">
                    {{ formatDateTime(event.timestamp) }}
                  </div>
                  <div>
                    <strong>{{ formatEventType(event.event_type) }}</strong>
                    @if (event.ip_address) {
                      <span class="text-muted small ms-2">({{ event.ip_address }})</span>
                    }
                    @if (event.detail && objectKeys(event.detail).length > 0) {
                      <div class="text-muted small">
                        @for (key of objectKeys(event.detail); track key) {
                          <span class="me-2">{{ key }}: {{ event.detail[key] }}</span>
                        }
                      </div>
                    }
                  </div>
                </li>
              }
            </ul>
          }
        </div>
      </div>
    }
  `,
})
export class SignatureRequestDetailComponent implements OnInit {
  request = signal<SignatureRequest | null>(null);
  auditEvents = signal<SignatureAuditEvent[]>([]);
  loading = signal(true);
  errorMsg = signal('');

  private requestId = 0;

  constructor(
    private route: ActivatedRoute,
    private esignatureService: EsignatureService,
  ) {}

  ngOnInit(): void {
    this.requestId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadRequest();
    this.loadAudit();
  }

  loadRequest(): void {
    this.loading.set(true);
    this.esignatureService.getRequest(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMsg.set(
          err.status === 404
            ? 'Signature request not found.'
            : 'Failed to load signature request.',
        );
        this.loading.set(false);
      },
    });
  }

  loadAudit(): void {
    this.esignatureService.getAuditTrail(this.requestId).subscribe({
      next: (events) => this.auditEvents.set(events),
    });
  }

  send(): void {
    this.esignatureService.sendRequest(this.requestId).subscribe({
      next: (updated) => {
        this.request.set(updated);
        this.loadAudit();
      },
    });
  }

  cancel(): void {
    if (!confirm('Cancel this signature request?')) return;
    this.esignatureService.cancelRequest(this.requestId).subscribe({
      next: (updated) => {
        this.request.set(updated);
        this.loadAudit();
      },
    });
  }

  remind(): void {
    this.esignatureService.remindSigners(this.requestId).subscribe({
      next: () => {
        alert('Reminder sent to pending signers.');
        this.loadAudit();
      },
    });
  }

  downloadCertificate(): void {
    this.esignatureService.downloadCertificate(this.requestId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `signature-certificate-${this.requestId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
    });
  }

  getStatusBadgeClass(status: string): Record<string, boolean> {
    return {
      'bg-secondary': status === 'draft',
      'bg-primary': status === 'sent',
      'bg-warning text-dark': status === 'in_progress',
      'bg-success': status === 'completed',
      'bg-danger': status === 'cancelled',
      'bg-dark': status === 'expired',
    };
  }

  getSignerStatusClass(status: string): Record<string, boolean> {
    return {
      'bg-secondary': status === 'pending',
      'bg-info text-dark': status === 'viewed',
      'bg-success': status === 'signed',
      'bg-danger': status === 'declined',
    };
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

  formatDateTime(dateString: string): string {
    return new Date(dateString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatEventType(eventType: string): string {
    return eventType
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  objectKeys(obj: Record<string, any>): string[] {
    return Object.keys(obj);
  }
}
