import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PortalConfig, DocumentRequest } from '../../models/portal.model';

@Component({
  selector: 'app-request-manager',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="container-fluid">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h4 class="mb-0"><i class="bi bi-send me-2"></i>Document Requests</h4>
        <button class="btn btn-primary btn-sm" (click)="showForm.set(!showForm())">
          <i class="bi" [ngClass]="showForm() ? 'bi-x' : 'bi-plus'"></i>
          {{ showForm() ? 'Cancel' : 'New Request' }}
        </button>
      </div>

      <!-- Create Form -->
      @if (showForm()) {
        <div class="card mb-4">
          <div class="card-header">Create Document Request</div>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Portal</label>
                <select
                  class="form-select form-select-sm"
                  [ngModel]="formPortal()"
                  (ngModelChange)="formPortal.set($event)"
                >
                  <option [ngValue]="0" disabled>Select portal...</option>
                  @for (p of portals(); track p.id) {
                    <option [ngValue]="p.id">{{ p.name }}</option>
                  }
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label">Title</label>
                <input
                  type="text"
                  class="form-control form-control-sm"
                  [ngModel]="formTitle()"
                  (ngModelChange)="formTitle.set($event)"
                />
              </div>
              <div class="col-12">
                <label class="form-label">Description</label>
                <textarea
                  class="form-control form-control-sm"
                  rows="2"
                  [ngModel]="formDescription()"
                  (ngModelChange)="formDescription.set($event)"
                ></textarea>
              </div>
              <div class="col-md-4">
                <label class="form-label">Assignee Email</label>
                <input
                  type="email"
                  class="form-control form-control-sm"
                  [ngModel]="formAssigneeEmail()"
                  (ngModelChange)="formAssigneeEmail.set($event)"
                />
              </div>
              <div class="col-md-4">
                <label class="form-label">Assignee Name</label>
                <input
                  type="text"
                  class="form-control form-control-sm"
                  [ngModel]="formAssigneeName()"
                  (ngModelChange)="formAssigneeName.set($event)"
                />
              </div>
              <div class="col-md-4">
                <label class="form-label">Deadline</label>
                <input
                  type="date"
                  class="form-control form-control-sm"
                  [ngModel]="formDeadline()"
                  (ngModelChange)="formDeadline.set($event)"
                />
              </div>
            </div>
            @if (formError()) {
              <div class="alert alert-danger mt-3 mb-0 py-2 small">{{ formError() }}</div>
            }
            <div class="mt-3">
              <button
                class="btn btn-primary btn-sm"
                (click)="createRequest()"
                [disabled]="!formPortal() || !formTitle() || !formAssigneeEmail()"
              >
                <i class="bi bi-check me-1"></i>Create
              </button>
              <button class="btn btn-outline-secondary btn-sm ms-2" (click)="showForm.set(false)">
                Cancel
              </button>
            </div>
          </div>
        </div>
      }

      <!-- Request List -->
      @if (loading()) {
        <div class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      } @else if (requests().length === 0) {
        <div class="text-center text-muted py-4">
          <i class="bi bi-send fs-1"></i>
          <p class="mt-2">No document requests yet.</p>
        </div>
      } @else {
        <div class="table-responsive">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Title</th>
                <th>Portal</th>
                <th>Assignee</th>
                <th>Deadline</th>
                <th>Status</th>
                <th>Sent</th>
                <th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (req of requests(); track req.id) {
                <tr>
                  <td>{{ req.title }}</td>
                  <td>{{ req.portal_name }}</td>
                  <td>
                    {{ req.assignee_name || req.assignee_email }}
                    <br *ngIf="req.assignee_name" />
                    <small *ngIf="req.assignee_name" class="text-muted">{{
                      req.assignee_email
                    }}</small>
                  </td>
                  <td>
                    @if (req.deadline) {
                      {{ req.deadline | date: 'mediumDate' }}
                    } @else {
                      <span class="text-muted">None</span>
                    }
                  </td>
                  <td>
                    <span
                      class="badge"
                      [ngClass]="getStatusBadgeClass(req.status)"
                    >
                      {{ req.status }}
                    </span>
                  </td>
                  <td>
                    @if (req.sent_at) {
                      {{ req.sent_at | date: 'short' }}
                    } @else {
                      <span class="text-muted">Not sent</span>
                    }
                  </td>
                  <td class="text-end">
                    @if (!req.sent_at) {
                      <button
                        class="btn btn-outline-success btn-sm me-1"
                        (click)="sendRequest(req)"
                        title="Send request email"
                      >
                        <i class="bi bi-envelope me-1"></i>Send
                      </button>
                    } @else {
                      <button
                        class="btn btn-outline-warning btn-sm me-1"
                        (click)="remindRequest(req)"
                        title="Send reminder email"
                      >
                        <i class="bi bi-bell me-1"></i>Remind
                      </button>
                    }
                    <a
                      [href]="'/request/' + req.token"
                      target="_blank"
                      class="btn btn-outline-info btn-sm"
                      title="Open public request page"
                    >
                      <i class="bi bi-box-arrow-up-right"></i>
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
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

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending':
        return 'bg-warning text-dark';
      case 'sent':
        return 'bg-info text-dark';
      case 'submitted':
        return 'bg-success';
      case 'expired':
        return 'bg-secondary';
      case 'cancelled':
        return 'bg-danger';
      default:
        return 'bg-secondary';
    }
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
