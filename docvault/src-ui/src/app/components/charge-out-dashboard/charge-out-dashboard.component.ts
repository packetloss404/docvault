import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PhysicalRecordService } from '../../services/physical-record.service';
import { ChargeOut } from '../../models/physical-record.model';

@Component({
  selector: 'app-charge-out-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h3 class="mb-0">Charge-Out Dashboard</h3>
    </div>

    <!-- Stats -->
    <div class="row mb-4">
      <div class="col-md-4">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title text-primary">{{ totalCheckedOut() }}</h5>
            <p class="card-text text-muted small mb-0">Currently Checked Out</p>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center border-danger">
          <div class="card-body">
            <h5 class="card-title text-danger">{{ overdueCount() }}</h5>
            <p class="card-text text-muted small mb-0">Overdue</p>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title text-success">{{ returnedCount() }}</h5>
            <p class="card-text text-muted small mb-0">Returned</p>
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
          <option value="checked_out">Checked Out</option>
          <option value="overdue">Overdue</option>
          <option value="returned">Returned</option>
        </select>
      </div>
      <div class="col-auto">
        <div class="input-group input-group-sm">
          <input
            type="text"
            class="form-control"
            placeholder="Search user or barcode..."
            [ngModel]="searchQuery()"
            (ngModelChange)="searchQuery.set($event)"
            (keyup.enter)="onSearch()"
          />
          <button class="btn btn-outline-secondary" (click)="onSearch()">
            <i class="bi bi-search"></i>
          </button>
        </div>
      </div>
    </div>

    @if (loading()) {
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (displayedChargeOuts().length === 0) {
      <div class="text-center text-muted py-5">
        <i class="bi bi-box-arrow-up-right fs-1"></i>
        <p class="mt-2">No charge-outs found.</p>
      </div>
    } @else {
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead>
            <tr>
              <th>Record</th>
              <th>User</th>
              <th>Checked Out</th>
              <th>Expected Return</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (co of displayedChargeOuts(); track co.id) {
              <tr [class.table-danger]="co.status === 'overdue'">
                <td>
                  <code>{{ co.record_barcode || '#' + co.physical_record }}</code>
                </td>
                <td>{{ co.user_name }}</td>
                <td>{{ formatDate(co.checked_out_at) }}</td>
                <td>
                  {{ formatDate(co.expected_return) }}
                  @if (isOverdue(co)) {
                    <i class="bi bi-exclamation-triangle text-danger ms-1" title="Overdue"></i>
                  }
                </td>
                <td>
                  <span
                    class="badge"
                    [ngClass]="getStatusBadgeClass(co.status)"
                  >
                    {{ formatStatus(co.status) }}
                  </span>
                </td>
                <td>
                  <span class="text-truncate d-inline-block" style="max-width: 150px;">
                    {{ co.notes }}
                  </span>
                </td>
                <td>
                  @if (co.status === 'checked_out' || co.status === 'overdue') {
                    <button
                      class="btn btn-sm btn-outline-success"
                      title="Check In"
                      (click)="checkIn(co)"
                    >
                      <i class="bi bi-box-arrow-in-down me-1"></i>Check In
                    </button>
                  } @else {
                    <span class="text-muted small">
                      {{ co.returned_at ? formatDate(co.returned_at) : '' }}
                    </span>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }

    <!-- Check-in Modal -->
    @if (checkingIn()) {
      <div
        class="modal d-block"
        tabindex="-1"
        style="background: rgba(0,0,0,0.5);"
      >
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Check In Record</h5>
              <button
                class="btn-close"
                (click)="checkingIn.set(null)"
              ></button>
            </div>
            <div class="modal-body">
              <label class="form-label">Notes (optional)</label>
              <textarea
                class="form-control"
                rows="3"
                [(ngModel)]="checkInNotes"
                placeholder="Return notes..."
              ></textarea>
            </div>
            <div class="modal-footer">
              <button
                class="btn btn-secondary"
                (click)="checkingIn.set(null)"
              >
                Cancel
              </button>
              <button class="btn btn-success" (click)="confirmCheckIn()">
                <i class="bi bi-check-lg me-1"></i>Confirm Check In
              </button>
            </div>
          </div>
        </div>
      </div>
    }
  `,
})
export class ChargeOutDashboardComponent implements OnInit {
  chargeOuts = signal<ChargeOut[]>([]);
  loading = signal(false);
  statusFilter = signal('');
  searchQuery = signal('');
  checkingIn = signal<ChargeOut | null>(null);
  checkInNotes = '';

  constructor(private physicalRecordService: PhysicalRecordService) {}

  ngOnInit(): void {
    this.loadChargeOuts();
  }

  loadChargeOuts(): void {
    this.loading.set(true);
    const params: Record<string, string> = {};
    const status = this.statusFilter();
    if (status) {
      params['status'] = status;
    }
    this.physicalRecordService.getChargeOuts(params).subscribe({
      next: (data) => {
        this.chargeOuts.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  displayedChargeOuts(): ChargeOut[] {
    const query = this.searchQuery().toLowerCase().trim();
    if (!query) return this.chargeOuts();
    return this.chargeOuts().filter(
      (co) =>
        co.user_name.toLowerCase().includes(query) ||
        (co.record_barcode && co.record_barcode.toLowerCase().includes(query)),
    );
  }

  totalCheckedOut(): number {
    return this.chargeOuts().filter(
      (co) => co.status === 'checked_out',
    ).length;
  }

  overdueCount(): number {
    return this.chargeOuts().filter(
      (co) => co.status === 'overdue',
    ).length;
  }

  returnedCount(): number {
    return this.chargeOuts().filter(
      (co) => co.status === 'returned',
    ).length;
  }

  onStatusFilterChange(value: string): void {
    this.statusFilter.set(value);
    this.loadChargeOuts();
  }

  onSearch(): void {
    // Local filtering via displayedChargeOuts()
  }

  isOverdue(co: ChargeOut): boolean {
    if (co.status === 'returned') return false;
    return new Date(co.expected_return) < new Date();
  }

  getStatusBadgeClass(status: string): Record<string, boolean> {
    return {
      'bg-primary': status === 'checked_out',
      'bg-danger': status === 'overdue',
      'bg-success': status === 'returned',
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

  checkIn(co: ChargeOut): void {
    this.checkingIn.set(co);
    this.checkInNotes = '';
  }

  confirmCheckIn(): void {
    const co = this.checkingIn();
    if (!co) return;

    // We need the document ID to call chargeIn.
    // The charge-out references the physical_record, which references a document.
    // We pass the physical_record ID -- but our API uses document_id.
    // For simplicity, we'll look it up through the record service.
    this.physicalRecordService
      .getRecord(co.physical_record)
      .subscribe({
        next: (record) => {
          this.physicalRecordService
            .chargeIn(record.document, { notes: this.checkInNotes })
            .subscribe({
              next: () => {
                this.checkingIn.set(null);
                this.loadChargeOuts();
              },
            });
        },
      });
  }
}
