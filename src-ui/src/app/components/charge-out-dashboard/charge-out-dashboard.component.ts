import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PhysicalRecordService } from '../../services/physical-record.service';
import { ChargeOut } from '../../models/physical-record.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-charge-out-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './charge-out-dashboard.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <!-- Stats -->
        <div class="co-stats">
          <div class="dv-stat dv-stat--sm">
            <div class="dv-stat__label">checked out</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value">{{ totalCheckedOut() }}</span>
            </div>
          </div>
          <div class="dv-stat dv-stat--sm co-stats__overdue">
            <div class="dv-stat__label">overdue</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value dv-danger">{{ overdueCount() }}</span>
            </div>
          </div>
          <div class="dv-stat dv-stat--sm">
            <div class="dv-stat__label">returned</div>
            <div class="dv-stat__row">
              <span class="dv-stat__value dv-ok">{{ returnedCount() }}</span>
            </div>
          </div>
        </div>

        <!-- Filters -->
        <div class="co-filters">
          <select
            class="dv-select co-select"
            aria-label="Filter by status"
            [ngModel]="statusFilter()"
            (ngModelChange)="onStatusFilterChange($event)"
          >
            <option value="">all statuses</option>
            <option value="checked_out">checked out</option>
            <option value="overdue">overdue</option>
            <option value="returned">returned</option>
          </select>

          <input
            type="search"
            class="dv-input dv-input--r7 co-search"
            placeholder="Filter by user or barcode…"
            aria-label="Filter by user or barcode"
            [ngModel]="searchQuery()"
            (ngModelChange)="searchQuery.set($event)"
            (keyup.enter)="onSearch()"
          />
        </div>

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (displayedChargeOuts().length === 0) {
          <div class="dv-empty">No charge-outs found.</div>
        } @else {
          <div class="co-table">
            <div
              class="dv-thead dv-grid"
              style="--dv-cols: 1.2fr 110px 100px 120px 96px 1fr 84px; --dv-gap: 12px"
            >
              <span>record</span>
              <span>charged to</span>
              <span>out since</span>
              <span>due back</span>
              <span>status</span>
              <span>notes</span>
              <span></span>
            </div>

            @for (co of displayedChargeOuts(); track co.id) {
              <div
                class="dv-row dv-grid dv-row--static"
                style="--dv-cols: 1.2fr 110px 100px 120px 96px 1fr 84px; --dv-gap: 12px"
              >
                <span class="dv-mono co-record dv-clip">{{
                  co.record_barcode || '#' + co.physical_record
                }}</span>
                <span class="co-who dv-clip">{{ co.user_name }}</span>
                <span class="dv-ts">{{ formatDate(co.checked_out_at) }}</span>
                <span class="dv-mono co-due" [ngClass]="dueClass(co)">{{ dueLabel(co) }}</span>
                <span>
                  <span class="dv-chip dv-chip--upper" [ngClass]="getStatusBadgeClass(co.status)">{{
                    formatStatus(co.status)
                  }}</span>
                </span>
                <span class="dv-muted dv-clip co-notes" [title]="co.notes">{{ co.notes }}</span>
                <span class="co-cell-right">
                  @if (co.status === 'checked_out' || co.status === 'overdue') {
                    <button
                      type="button"
                      class="dv-rowaction dv-rowaction--accent"
                      title="Check in"
                      (click)="checkIn(co)"
                    >
                      check in
                    </button>
                  } @else if (co.returned_at) {
                    <span class="dv-meta">{{ formatDate(co.returned_at) }}</span>
                  }
                </span>
              </div>
            }
          </div>
        }
      </div>
    </div>

    <!-- Check-in dialog -->
    @if (checkingIn()) {
      <div class="dv-overlay" (click)="checkingIn.set(null)">
        <div
          class="dv-modal"
          role="dialog"
          aria-modal="true"
          aria-label="Check in record"
          (click)="$event.stopPropagation()"
        >
          <div class="dv-modal__head">
            <span>Check in record</span>
            <button
              type="button"
              class="dv-modal__close"
              aria-label="Close"
              (click)="checkingIn.set(null)"
            >
              ✕
            </button>
          </div>

          <div class="dv-modal__body co-modal__body">
            <div class="dv-meta">
              {{ checkingIn()!.record_barcode || '#' + checkingIn()!.physical_record }} ·
              {{ checkingIn()!.user_name }}
            </div>
            <label>
              <span class="dv-field__label">return notes</span>
              <textarea
                class="dv-input dv-input--r7"
                rows="3"
                placeholder="Return notes…"
                [(ngModel)]="checkInNotes"
              ></textarea>
            </label>
          </div>

          <div class="dv-modal__foot">
            <button
              type="button"
              class="dv-btn dv-btn--ghost dv-btn--md dv-push"
              (click)="checkingIn.set(null)"
            >
              Cancel
            </button>
            <button type="button" class="dv-btn dv-btn--primary dv-btn--md" (click)="confirmCheckIn()">
              Confirm check in
            </button>
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

  /** Mono due-back readout; overdue records say so in words. */
  dueLabel(co: ChargeOut): string {
    const due = this.formatDate(co.expected_return);
    return this.isOverdue(co) ? `overdue ${due}` : due;
  }

  dueClass(co: ChargeOut): string {
    if (this.isOverdue(co)) return 'dv-danger';
    return co.status === 'returned' ? 'dv-faint' : 'dv-muted';
  }

  /** Console status chip modifier for a charge-out status. */
  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'checked_out':
        return 'dv-chip--accent';
      case 'overdue':
        return 'dv-chip--danger';
      case 'returned':
        return 'dv-chip--ok';
      default:
        return '';
    }
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
