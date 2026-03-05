import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { LegalHoldService } from '../../services/legal-hold.service';
import {
  LegalHold,
  LegalHoldCustodian,
  LegalHoldDocument,
} from '../../models/legal-hold.model';

@Component({
  selector: 'app-legal-hold-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    @if (loading()) {
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (hold()) {
      <!-- Header -->
      <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
          <a routerLink="/legal-holds" class="text-decoration-none small">
            <i class="bi bi-arrow-left me-1"></i>Back to Legal Holds
          </a>
          <h3 class="mt-2 mb-1">{{ hold()!.name }}</h3>
          <div class="d-flex align-items-center gap-2">
            <span
              class="badge"
              [ngClass]="getStatusBadgeClass(hold()!.status)"
            >
              {{ formatStatus(hold()!.status) }}
            </span>
            <code class="text-muted">{{ hold()!.matter_number }}</code>
          </div>
        </div>
        <div class="btn-group">
          @if (hold()!.status === 'draft') {
            <button class="btn btn-danger" (click)="activate()">
              <i class="bi bi-play-fill me-1"></i>Activate Hold
            </button>
          }
          @if (hold()!.status === 'active') {
            <button class="btn btn-warning" (click)="notifyCustodians()">
              <i class="bi bi-bell me-1"></i>Notify Custodians
            </button>
            <button class="btn btn-success" (click)="release()">
              <i class="bi bi-unlock me-1"></i>Release Hold
            </button>
          }
        </div>
      </div>

      <!-- Details Card -->
      <div class="card mb-4">
        <div class="card-header">Hold Details</div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-8">
              <p class="mb-2">{{ hold()!.description || 'No description provided.' }}</p>
            </div>
            <div class="col-md-4">
              <dl class="row mb-0">
                <dt class="col-sm-6">Created</dt>
                <dd class="col-sm-6">{{ formatDate(hold()!.created_at) }}</dd>
                @if (hold()!.activated_at) {
                  <dt class="col-sm-6">Activated</dt>
                  <dd class="col-sm-6">{{ formatDate(hold()!.activated_at!) }}</dd>
                }
                @if (hold()!.released_at) {
                  <dt class="col-sm-6">Released</dt>
                  <dd class="col-sm-6">{{ formatDate(hold()!.released_at!) }}</dd>
                }
                @if (hold()!.release_reason) {
                  <dt class="col-sm-6">Reason</dt>
                  <dd class="col-sm-6">{{ hold()!.release_reason }}</dd>
                }
              </dl>
            </div>
          </div>
        </div>
      </div>

      <!-- Stats Row -->
      <div class="row mb-4">
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <h5 class="card-title">{{ hold()!.criteria_count }}</h5>
              <p class="card-text text-muted small mb-0">Criteria</p>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <h5 class="card-title">{{ documents().length }}</h5>
              <p class="card-text text-muted small mb-0">Held Documents</p>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <h5 class="card-title">{{ custodians().length }}</h5>
              <p class="card-text text-muted small mb-0">Custodians</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Held Documents -->
      <div class="card mb-4">
        <div class="card-header">
          Held Documents
          <span class="badge bg-primary ms-2">{{ documents().length }}</span>
        </div>
        <div class="card-body p-0">
          @if (documents().length === 0) {
            <div class="text-center text-muted py-4">
              No documents under this hold.
            </div>
          } @else {
            <div class="table-responsive">
              <table class="table table-hover mb-0">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Held At</th>
                    <th>Released At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (doc of documents(); track doc.id) {
                    <tr>
                      <td>
                        <a
                          [routerLink]="['/documents', doc.document]"
                          class="text-decoration-none"
                        >
                          {{ doc.document_title }}
                        </a>
                      </td>
                      <td>{{ formatDate(doc.held_at) }}</td>
                      <td>
                        @if (doc.released_at) {
                          {{ formatDate(doc.released_at) }}
                        } @else {
                          <span class="badge bg-danger">Held</span>
                        }
                      </td>
                      <td>
                        <a
                          class="btn btn-sm btn-outline-secondary"
                          [routerLink]="['/documents', doc.document]"
                          title="View Document"
                        >
                          <i class="bi bi-eye"></i>
                        </a>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>
      </div>

      <!-- Custodians -->
      <div class="card mb-4">
        <div class="card-header">
          Custodians
          <span class="badge bg-primary ms-2">{{ custodians().length }}</span>
        </div>
        <div class="card-body p-0">
          @if (custodians().length === 0) {
            <div class="text-center text-muted py-4">
              No custodians assigned to this hold.
            </div>
          } @else {
            <div class="table-responsive">
              <table class="table table-hover mb-0">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Notified At</th>
                    <th>Acknowledged</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  @for (custodian of custodians(); track custodian.id) {
                    <tr>
                      <td>{{ custodian.user_name }}</td>
                      <td>
                        @if (custodian.notified_at) {
                          {{ formatDate(custodian.notified_at) }}
                        } @else {
                          <span class="text-muted">Not notified</span>
                        }
                      </td>
                      <td>
                        @if (custodian.acknowledged) {
                          <span class="badge bg-success">
                            <i class="bi bi-check-lg me-1"></i>
                            {{ custodian.acknowledged_at ? formatDate(custodian.acknowledged_at) : 'Yes' }}
                          </span>
                        } @else {
                          <span class="badge bg-warning text-dark">Pending</span>
                        }
                      </td>
                      <td>{{ custodian.notes }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>
      </div>
    }
  `,
})
export class LegalHoldDetailComponent implements OnInit {
  hold = signal<LegalHold | null>(null);
  documents = signal<LegalHoldDocument[]>([]);
  custodians = signal<LegalHoldCustodian[]>([]);
  loading = signal(false);

  private holdId = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private legalHoldService: LegalHoldService,
  ) {}

  ngOnInit(): void {
    this.holdId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadHold();
  }

  loadHold(): void {
    this.loading.set(true);
    this.legalHoldService.getHold(this.holdId).subscribe({
      next: (hold) => {
        this.hold.set(hold);
        this.loading.set(false);
        this.loadDocuments();
        this.loadCustodians();
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  loadDocuments(): void {
    this.legalHoldService.getHoldDocuments(this.holdId).subscribe({
      next: (docs) => this.documents.set(docs),
    });
  }

  loadCustodians(): void {
    this.legalHoldService.getHoldCustodians(this.holdId).subscribe({
      next: (custodians) => this.custodians.set(custodians),
    });
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

  activate(): void {
    const hold = this.hold();
    if (!hold) return;
    if (
      !confirm(
        `Activate legal hold "${hold.name}"? This will freeze all matching documents.`,
      )
    ) {
      return;
    }
    this.legalHoldService.activateHold(hold.id).subscribe({
      next: () => this.loadHold(),
    });
  }

  release(): void {
    const hold = this.hold();
    if (!hold) return;
    const reason = prompt(`Reason for releasing hold "${hold.name}":`);
    if (reason === null) return;
    this.legalHoldService.releaseHold(hold.id, reason).subscribe({
      next: () => this.loadHold(),
    });
  }

  notifyCustodians(): void {
    this.legalHoldService.notifyCustodians(this.holdId).subscribe({
      next: (result) => {
        alert(`Notified ${result.notified} custodian(s).`);
        this.loadCustodians();
      },
    });
  }
}
