import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PortalConfig, DocumentRequest } from '../../models/portal.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-request-manager',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './request-manager.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-section rm-section">
          <span class="dv-eyebrow">document requests</span>
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--md dv-push"
            (click)="showForm.set(!showForm())"
          >
            {{ showForm() ? 'Cancel' : '+ New request' }}
          </button>
        </div>

        <!-- Create form -->
        @if (showForm()) {
          <div class="dv-card dv-card--pad rm-form">
            <div class="dv-card__title rm-form__title">Create document request</div>

            <div class="rm-grid">
              <label class="rm-field">
                <span class="dv-field__label">portal</span>
                <select
                  class="dv-select dv-input--r7"
                  [ngModel]="formPortal()"
                  (ngModelChange)="formPortal.set($event)"
                >
                  <option [ngValue]="0" disabled>select portal…</option>
                  @for (p of portals(); track p.id) {
                    <option [ngValue]="p.id">{{ p.name }}</option>
                  }
                </select>
              </label>

              <label class="rm-field">
                <span class="dv-field__label">title</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  [ngModel]="formTitle()"
                  (ngModelChange)="formTitle.set($event)"
                />
              </label>

              <label class="rm-field rm-field--full">
                <span class="dv-field__label">description</span>
                <textarea
                  class="dv-input dv-input--r7"
                  rows="2"
                  [ngModel]="formDescription()"
                  (ngModelChange)="formDescription.set($event)"
                ></textarea>
              </label>

              <label class="rm-field">
                <span class="dv-field__label">assignee email</span>
                <input
                  type="email"
                  class="dv-input dv-input--r7 dv-mono"
                  [ngModel]="formAssigneeEmail()"
                  (ngModelChange)="formAssigneeEmail.set($event)"
                />
              </label>

              <label class="rm-field">
                <span class="dv-field__label">assignee name</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  [ngModel]="formAssigneeName()"
                  (ngModelChange)="formAssigneeName.set($event)"
                />
              </label>

              <label class="rm-field">
                <span class="dv-field__label">deadline</span>
                <input
                  type="date"
                  class="dv-input dv-input--r7 dv-mono"
                  [ngModel]="formDeadline()"
                  (ngModelChange)="formDeadline.set($event)"
                />
              </label>
            </div>

            @if (formError()) {
              <div class="dv-banner dv-banner--error rm-banner" role="alert">{{ formError() }}</div>
            }

            <div class="rm-form__actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--md"
                (click)="createRequest()"
                [disabled]="!formPortal() || !formTitle() || !formAssigneeEmail()"
              >
                Create
              </button>
              <button
                type="button"
                class="dv-btn dv-btn--ghost dv-btn--md"
                (click)="showForm.set(false)"
              >
                Cancel
              </button>
            </div>
          </div>
        }

        <!-- Request rows -->
        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (requests().length === 0) {
          <div class="dv-empty">No document requests yet.</div>
        } @else {
          <div class="rm-list">
            @for (req of requests(); track req.id) {
              <div class="dv-card dv-card--r10 rm-row">
                <div class="rm-row__main">
                  <div class="rm-row__title dv-clip">{{ req.title }}</div>
                  <div class="dv-meta rm-row__meta">
                    for @if (req.assignee_name) {
                      {{ req.assignee_name }} ·
                    }
                    {{ req.assignee_email }} · {{ req.portal_name }} · token /request/{{
                      req.token
                    }}
                    @if (req.sent_at) {
                      · sent {{ req.sent_at | date: 'short' }}
                    } @else {
                      · not sent
                    }
                  </div>
                </div>

                <span class="dv-chip dv-chip--upper" [ngClass]="getStatusBadgeClass(req.status)">{{
                  req.status
                }}</span>

                <span class="dv-meta rm-row__when" [ngClass]="deadlineClass(req)">{{
                  deadlineLabel(req)
                }}</span>

                @if (!req.sent_at) {
                  <button
                    type="button"
                    class="dv-rowaction dv-rowaction--accent"
                    (click)="sendRequest(req)"
                    title="Send request email"
                  >
                    send
                  </button>
                } @else {
                  <button
                    type="button"
                    class="dv-rowaction dv-rowaction--accent"
                    (click)="remindRequest(req)"
                    title="Send reminder email"
                  >
                    remind
                  </button>
                }

                <a
                  class="dv-rowaction dv-rowaction--accent"
                  [href]="'/request/' + req.token"
                  target="_blank"
                  rel="noopener"
                  title="Open public request page"
                  >⧉</a
                >
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class RequestManagerComponent implements OnInit {
  requests = signal<DocumentRequest[]>([]);
  portals = signal<PortalConfig[]>([]);
  loading = signal(true);
  showForm = signal(false);
  formError = signal('');

  formPortal = signal<number>(0);
  formTitle = signal('');
  formDescription = signal('');
  formAssigneeEmail = signal('');
  formAssigneeName = signal('');
  formDeadline = signal('');

  constructor(private portalService: PortalService) {}

  ngOnInit(): void {
    this.loadRequests();
    this.loadPortals();
  }

  loadPortals(): void {
    this.portalService.getPortals().subscribe({
      next: (resp) => this.portals.set(resp.results),
    });
  }

  loadRequests(): void {
    this.loading.set(true);
    this.portalService.getRequests().subscribe({
      next: (resp) => {
        this.requests.set(resp.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  /** Console status chip modifier for a request status. */
  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending':
        return 'dv-chip--warn';
      case 'sent':
        return 'dv-chip--accent';
      case 'submitted':
        return 'dv-chip--ok';
      case 'expired':
        return 'dv-chip--danger';
      default:
        return '';
    }
  }

  /** Mono clock readout for the deadline column. */
  deadlineLabel(req: DocumentRequest): string {
    if (!req.deadline) return 'no deadline';
    return this.isOverdue(req)
      ? `overdue ${this.formatDay(req.deadline)}`
      : `due ${this.formatDay(req.deadline)}`;
  }

  deadlineClass(req: DocumentRequest): string {
    if (!req.deadline) return 'dv-faint';
    return this.isOverdue(req) ? 'dv-danger' : '';
  }

  isOverdue(req: DocumentRequest): boolean {
    if (!req.deadline || req.status === 'submitted' || req.status === 'cancelled') {
      return false;
    }
    return new Date(req.deadline) < new Date();
  }

  formatDay(dateString: string): string {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  }

  createRequest(): void {
    this.formError.set('');
    const data: Partial<DocumentRequest> = {
      portal: this.formPortal(),
      title: this.formTitle(),
      description: this.formDescription(),
      assignee_email: this.formAssigneeEmail(),
      assignee_name: this.formAssigneeName(),
      deadline: this.formDeadline() || null,
    };
    this.portalService.createRequest(data).subscribe({
      next: () => {
        this.showForm.set(false);
        this.resetForm();
        this.loadRequests();
      },
      error: (err) => {
        this.formError.set(
          err.error?.detail || JSON.stringify(err.error) || 'Create failed.',
        );
      },
    });
  }

  private resetForm(): void {
    this.formPortal.set(0);
    this.formTitle.set('');
    this.formDescription.set('');
    this.formAssigneeEmail.set('');
    this.formAssigneeName.set('');
    this.formDeadline.set('');
    this.formError.set('');
  }

  sendRequest(req: DocumentRequest): void {
    if (!confirm(`Send request "${req.title}" to ${req.assignee_email}?`)) return;
    this.portalService.sendRequest(req.id).subscribe({
      next: () => this.loadRequests(),
    });
  }

  remindRequest(req: DocumentRequest): void {
    if (!confirm(`Send reminder for "${req.title}" to ${req.assignee_email}?`)) return;
    this.portalService.remindRequest(req.id).subscribe({
      next: () => this.loadRequests(),
    });
  }
}
