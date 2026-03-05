import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { LegalHoldService } from '../../services/legal-hold.service';
import { LegalHold } from '../../models/legal-hold.model';

@Component({
  selector: 'app-legal-hold-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h3 class="mb-0">Legal Holds</h3>
      <button class="btn btn-primary" (click)="showCreateForm = true">
        <i class="bi bi-plus-lg me-1"></i>New Hold
      </button>
    </div>

    <!-- Stats -->
    <div class="row mb-4">
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title text-danger">{{ activeCount() }}</h5>
            <p class="card-text text-muted small mb-0">Active Holds</p>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title text-primary">{{ totalDocumentsHeld() }}</h5>
            <p class="card-text text-muted small mb-0">Documents Held</p>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title text-secondary">{{ draftCount() }}</h5>
            <p class="card-text text-muted small mb-0">Draft Holds</p>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title text-success">{{ releasedCount() }}</h5>
            <p class="card-text text-muted small mb-0">Released</p>
          </div>
        </div>
      </div>
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
          <option value="active">Active</option>
          <option value="released">Released</option>
        </select>
      </div>
    </div>

    <!-- Create Form Modal -->
    @if (showCreateForm) {
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Create Legal Hold</span>
          <button class="btn-close" (click)="showCreateForm = false"></button>
        </div>
        <div class="card-body">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Name</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="newHold.name"
                placeholder="Hold name"
              />
            </div>
            <div class="col-md-6">
              <label class="form-label">Matter Number</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="newHold.matter_number"
                placeholder="e.g., CASE-2024-001"
              />
            </div>
            <div class="col-12">
              <label class="form-label">Description</label>
              <textarea
                class="form-control"
                rows="3"
                [(ngModel)]="newHold.description"
                placeholder="Description of the legal hold..."
              ></textarea>
            </div>
            <div class="col-12">
              <button class="btn btn-primary me-2" (click)="createHold()">
                Create Hold
              </button>
              <button
                class="btn btn-secondary"
                (click)="showCreateForm = false"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    }

    @if (loading()) {
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (filteredHolds().length === 0) {
      <div class="text-center text-muted py-5">
        <i class="bi bi-shield-lock fs-1"></i>
        <p class="mt-2">No legal holds found.</p>
      </div>
    } @else {
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead>
            <tr>
              <th>Name</th>
              <th>Matter Number</th>
              <th>Status</th>
              <th>Documents</th>
              <th>Custodians</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (hold of filteredHolds(); track hold.id) {
              <tr>
                <td>
                  <a
                    [routerLink]="['/legal-holds', hold.id]"
                    class="text-decoration-none fw-semibold"
                  >
                    {{ hold.name }}
                  </a>
                </td>
                <td>
                  <code>{{ hold.matter_number }}</code>
                </td>
                <td>
                  <span
                    class="badge"
                    [ngClass]="getStatusBadgeClass(hold.status)"
                  >
                    {{ formatStatus(hold.status) }}
                  </span>
                </td>
                <td>
                  <span class="badge bg-light text-dark">
                    {{ hold.document_count }}
                  </span>
                </td>
                <td>
                  <span class="badge bg-light text-dark">
                    {{ hold.custodian_count }}
                  </span>
                </td>
                <td>{{ formatDate(hold.created_at) }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <a
                      class="btn btn-outline-secondary"
                      [routerLink]="['/legal-holds', hold.id]"
                      title="View Details"
                    >
                      <i class="bi bi-eye"></i>
                    </a>
                    @if (hold.status === 'draft') {
                      <button
                        class="btn btn-outline-danger"
                        title="Activate"
                        (click)="activateHold(hold)"
                      >
                        <i class="bi bi-play-fill"></i>
                      </button>
                    }
                    @if (hold.status === 'active') {
                      <button
                        class="btn btn-outline-success"
                        title="Release"
                        (click)="releaseHold(hold)"
                      >
                        <i class="bi bi-unlock"></i>
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

  getStatusBadgeClass(
    status: LegalHold['status'],
  ): Record<string, boolean> {
    return {
      'bg-secondary': status === 'draft',
      'bg-danger': status === 'active',
      'bg-success': status === 'released',
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
