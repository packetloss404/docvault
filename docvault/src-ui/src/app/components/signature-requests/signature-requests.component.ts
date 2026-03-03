import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { EsignatureService } from '../../services/esignature.service';
import { SignatureRequest } from '../../models/esignature.model';

@Component({
  selector: 'app-signature-requests',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h3 class="mb-0">E-Signature Requests</h3>
      <button class="btn btn-primary" routerLink="/documents">
        <i class="bi bi-plus-lg me-1"></i>New Request
      </button>
    </div>

    <!-- Filters -->
    <div class="row mb-3">
      <div class="col-auto">
        <select
          class="form-select form-select-sm"
          [ngModel]="statusFilter()"
          (ngModelChange)="onStatusFilterChange($event)"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="sent">Sent</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
          <option value="expired">Expired</option>
        </select>
      </div>
    </div>

    @if (loading()) {
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (filteredRequests().length === 0) {
      <div class="text-center text-muted py-5">
        <i class="bi bi-pen fs-1"></i>
        <p class="mt-2">No signature requests found.</p>
      </div>
    } @else {
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead>
            <tr>
              <th>Title</th>
              <th>Document</th>
              <th>Signers</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (req of filteredRequests(); track req.id) {
              <tr>
                <td>
                  <a [routerLink]="['/signature-requests', req.id]" class="text-decoration-none">
                    {{ req.title }}
                  </a>
                </td>
                <td>
                  <a [routerLink]="['/documents', req.document]" class="text-decoration-none">
                    #{{ req.document }}
                  </a>
                </td>
                <td>
                  <span class="badge bg-light text-dark">
                    {{ req.signers.length }} signer{{ req.signers.length !== 1 ? 's' : '' }}
                  </span>
                </td>
                <td>
                  <span class="badge" [ngClass]="getStatusBadgeClass(req.status)">
                    {{ formatStatus(req.status) }}
                  </span>
                </td>
                <td>{{ formatDate(req.created_at) }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <a
                      class="btn btn-outline-secondary"
                      [routerLink]="['/signature-requests', req.id]"
                      title="View"
                    >
                      <i class="bi bi-eye"></i>
                    </a>
                    @if (req.status === 'sent' || req.status === 'in_progress') {
                      <button
                        class="btn btn-outline-warning"
                        title="Remind Signers"
                        (click)="remind(req)"
                      >
                        <i class="bi bi-bell"></i>
                      </button>
                      <button
                        class="btn btn-outline-danger"
                        title="Cancel"
                        (click)="cancel(req)"
                      >
                        <i class="bi bi-x-circle"></i>
                      </button>
                    }
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
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

  getStatusBadgeClass(
    status: SignatureRequest['status'],
  ): Record<string, boolean> {
    return {
      'bg-secondary': status === 'draft',
      'bg-primary': status === 'sent',
      'bg-warning text-dark': status === 'in_progress',
      'bg-success': status === 'completed',
      'bg-danger': status === 'cancelled',
      'bg-dark': status === 'expired',
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
