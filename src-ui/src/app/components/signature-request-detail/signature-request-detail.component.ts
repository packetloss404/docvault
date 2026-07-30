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
  styleUrl: './signature-request-detail.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (errorMsg()) {
          <div class="dv-banner dv-banner--error srd-banner" role="alert">{{ errorMsg() }}</div>
        } @else if (request()) {
          <a class="dv-meta srd-back" routerLink="/signature-requests">← signature requests</a>

          <div class="dv-pagehead srd-head">
            <h1 class="dv-h1 dv-h1--sm dv-clip">{{ request()!.title }}</h1>
            <span
              class="dv-chip dv-chip--upper"
              [ngClass]="getStatusBadgeClass(request()!.status)"
              >{{ formatStatus(request()!.status) }}</span
            >

            <div class="srd-actions dv-push">
              @if (request()!.status === 'draft') {
                <button type="button" class="dv-btn dv-btn--primary dv-btn--md" (click)="send()">
                  Send →
                </button>
              }
              @if (request()!.status === 'sent' || request()!.status === 'in_progress') {
                <button type="button" class="dv-btn dv-btn--warn dv-btn--md" (click)="remind()">
                  Remind
                </button>
                <button type="button" class="dv-btn dv-btn--danger dv-btn--md" (click)="cancel()">
                  Cancel
                </button>
              }
              @if (request()!.status === 'completed') {
                <button
                  type="button"
                  class="dv-btn dv-btn--accent dv-btn--md"
                  (click)="downloadCertificate()"
                >
                  Download certificate
                </button>
              }
            </div>
          </div>

          <!-- Request details -->
          <div class="dv-card dv-card--pad srd-card">
            <div class="dv-kv">
              <span class="dv-kv__k">document</span>
              <span
                ><a class="dv-link dv-mono" [routerLink]="['/documents', request()!.document]"
                  >#{{ request()!.document }}</a
                ></span
              >

              <span class="dv-kv__k">signing order</span>
              <span class="dv-mono">{{ request()!.signing_order }}</span>

              <span class="dv-kv__k">expiration</span>
              <span class="dv-mono">{{
                request()!.expiration ? formatDate(request()!.expiration!) : 'none'
              }}</span>

              <span class="dv-kv__k">completed at</span>
              <span class="dv-mono">{{
                request()!.completed_at ? formatDate(request()!.completed_at!) : '—'
              }}</span>

              <span class="dv-kv__k">created</span>
              <span class="dv-mono">{{ formatDate(request()!.created_at) }}</span>

              @if (request()!.message) {
                <span class="dv-kv__k">message</span>
                <span class="srd-message">{{ request()!.message }}</span>
              }
            </div>
          </div>

          <!-- Signers -->
          <div class="dv-section srd-section">
            <span class="dv-eyebrow">signers</span>
            <span class="dv-meta dv-push">{{ request()!.signers.length }}</span>
          </div>

          <div class="dv-thead dv-grid" style="--dv-cols: 34px 1fr 1.2fr 90px 96px 120px">
            <span>#</span><span>name</span><span>email</span><span>role</span><span>status</span
            ><span>signed</span>
          </div>
          @for (signer of request()!.signers; track signer.id) {
            <div
              class="dv-row dv-grid dv-row--static dv-row--tight"
              style="--dv-cols: 34px 1fr 1.2fr 90px 96px 120px"
            >
              <span class="dv-mono dv-faint">{{ signer.order }}</span>
              <span class="dv-clip srd-name">{{ signer.name }}</span>
              <span class="dv-mono dv-muted dv-clip srd-email">{{ signer.email }}</span>
              <span class="dv-mono dv-muted dv-clip">{{ signer.role }}</span>
              <span
                ><span class="dv-chip dv-chip--upper" [ngClass]="getSignerStatusClass(signer.status)"
                  >{{ formatStatus(signer.status) }}</span
                ></span
              >
              <span class="dv-ts">{{ signer.signed_at ? formatDate(signer.signed_at) : '—' }}</span>
            </div>
          }
          @if (request()!.signers.length === 0) {
            <div class="dv-empty">No signers on this request.</div>
          }

          <!-- Audit trail -->
          <div class="dv-section srd-section">
            <span class="dv-eyebrow">audit trail</span>
          </div>

          <div class="dv-card dv-card--pad">
            @if (auditEvents().length === 0) {
              <div class="dv-meta">No audit events yet.</div>
            } @else {
              <div class="dv-timeline">
                @for (event of auditEvents(); track event.id) {
                  <div class="dv-timeline__item">
                    <span class="dv-dot dv-timeline__dot" [ngClass]="eventDotClass(event.event_type)"></span>
                    <div class="dv-timeline__body">
                      <span class="srd-event">{{ formatEventType(event.event_type) }}</span>
                      @if (event.ip_address) {
                        <span class="dv-meta srd-ip">{{ event.ip_address }}</span>
                      }
                      @if (event.detail && objectKeys(event.detail).length > 0) {
                        <div class="dv-meta srd-detail">
                          @for (key of objectKeys(event.detail); track key) {
                            <span>{{ key }}: {{ event.detail[key] }}</span>
                          }
                        </div>
                      }
                      <div class="dv-timeline__when">{{ formatDateTime(event.timestamp) }}</div>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        }
      </div>
    </div>
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

  /** Console status chip modifier for a request status. */
  getStatusBadgeClass(status: string): string {
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

  getSignerStatusClass(status: string): string {
    switch (status) {
      case 'viewed':
        return 'dv-chip--accent';
      case 'signed':
        return 'dv-chip--ok';
      case 'declined':
        return 'dv-chip--danger';
      default:
        return '';
    }
  }

  /** Timeline dot colour by audit event class. */
  eventDotClass(eventType: string): string {
    const type = eventType.toLowerCase();
    if (type.includes('signed') || type.includes('completed')) return 'dv-dot--ok';
    if (type.includes('declined') || type.includes('cancel') || type.includes('expire'))
      return 'dv-dot--danger';
    if (type.includes('remind') || type.includes('sent')) return 'dv-dot--warn';
    if (type.includes('viewed') || type.includes('created')) return 'dv-dot--accent';
    return '';
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
