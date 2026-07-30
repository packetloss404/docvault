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
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-legal-hold-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './legal-hold-detail.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (hold()) {
          <a class="dv-meta lhd-back" routerLink="/legal-holds">← legal holds</a>

          <div class="dv-pagehead lhd-head">
            <h1 class="dv-h1 dv-h1--sm dv-clip">{{ hold()!.name }}</h1>
            <span class="dv-chip dv-chip--upper" [ngClass]="getStatusBadgeClass(hold()!.status)">{{
              formatStatus(hold()!.status)
            }}</span>
            <span class="dv-chip dv-chip--well">{{ hold()!.matter_number }}</span>

            <div class="lhd-actions dv-push">
              @if (hold()!.status === 'draft') {
                <button type="button" class="dv-btn dv-btn--danger dv-btn--md" (click)="activate()">
                  Activate hold
                </button>
              }
              @if (hold()!.status === 'active') {
                <button
                  type="button"
                  class="dv-btn dv-btn--warn dv-btn--md"
                  (click)="notifyCustodians()"
                >
                  Notify custodians
                </button>
                <button type="button" class="dv-btn dv-btn--ghost dv-btn--md" (click)="release()">
                  Release hold
                </button>
              }
            </div>
          </div>

          @if (hold()!.status === 'active') {
            <div class="dv-callout lhd-callout">
              <div class="dv-callout__label">preservation active</div>
              <div class="lhd-callout__text">
                Document mutations are blocked with HTTP 409 while this hold is active.
              </div>
            </div>
          }

          <!-- Details -->
          <div class="dv-card dv-card--pad lhd-card">
            <p class="lhd-desc">{{ hold()!.description || 'No description provided.' }}</p>
            <div class="dv-kv">
              <span class="dv-kv__k">created</span>
              <span class="dv-mono">{{ formatDate(hold()!.created_at) }}</span>

              @if (hold()!.activated_at) {
                <span class="dv-kv__k">activated</span>
                <span class="dv-mono">{{ formatDate(hold()!.activated_at!) }}</span>
              }
              @if (hold()!.released_at) {
                <span class="dv-kv__k">released</span>
                <span class="dv-mono">{{ formatDate(hold()!.released_at!) }}</span>
              }
              @if (hold()!.release_reason) {
                <span class="dv-kv__k">reason</span>
                <span>{{ hold()!.release_reason }}</span>
              }
            </div>
          </div>

          <!-- Stats -->
          <div class="lhd-stats">
            <div class="dv-stat dv-stat--sm">
              <div class="dv-stat__label">criteria</div>
              <div class="dv-stat__row">
                <span class="dv-stat__value">{{ hold()!.criteria_count }}</span>
              </div>
            </div>
            <div class="dv-stat dv-stat--sm">
              <div class="dv-stat__label">held documents</div>
              <div class="dv-stat__row">
                <span class="dv-stat__value">{{ documents().length }}</span>
              </div>
            </div>
            <div class="dv-stat dv-stat--sm">
              <div class="dv-stat__label">custodians</div>
              <div class="dv-stat__row">
                <span class="dv-stat__value">{{ custodians().length }}</span>
              </div>
            </div>
          </div>

          <!-- Held documents -->
          <div class="dv-section lhd-section">
            <span class="dv-eyebrow">held documents</span>
            <span class="dv-meta dv-push">{{ documents().length }}</span>
          </div>

          @if (documents().length === 0) {
            <div class="dv-empty">No documents under this hold.</div>
          } @else {
            <div class="dv-thead dv-grid" style="--dv-cols: 1fr 120px 150px; --dv-gap: 12px">
              <span>document</span><span>held</span><span>released</span>
            </div>
            @for (doc of documents(); track doc.id) {
              <a
                class="dv-row dv-grid"
                style="--dv-cols: 1fr 120px 150px; --dv-gap: 12px"
                [routerLink]="['/documents', doc.document]"
                title="View document"
              >
                <span class="lhd-doc dv-clip">{{ doc.document_title }}</span>
                <span class="dv-ts">{{ formatDate(doc.held_at) }}</span>
                <span>
                  @if (doc.released_at) {
                    <span class="dv-ts">{{ formatDate(doc.released_at) }}</span>
                  } @else {
                    <span class="dv-chip dv-chip--upper dv-chip--danger">held</span>
                  }
                </span>
              </a>
            }
          }

          <!-- Custodians -->
          <div class="dv-section lhd-section">
            <span class="dv-eyebrow">custodians</span>
            <span class="dv-meta dv-push">{{ custodians().length }}</span>
          </div>

          @if (custodians().length === 0) {
            <div class="dv-empty">No custodians assigned to this hold.</div>
          } @else {
            <div
              class="dv-thead dv-grid"
              style="--dv-cols: 1fr 130px 150px 1fr; --dv-gap: 12px"
            >
              <span>user</span><span>notified</span><span>acknowledged</span><span>notes</span>
            </div>
            @for (custodian of custodians(); track custodian.id) {
              <div
                class="dv-row dv-grid dv-row--static"
                style="--dv-cols: 1fr 130px 150px 1fr; --dv-gap: 12px"
              >
                <span class="lhd-doc dv-clip">{{ custodian.user_name }}</span>
                <span>
                  @if (custodian.notified_at) {
                    <span class="dv-ts">{{ formatDate(custodian.notified_at) }}</span>
                  } @else {
                    <span class="dv-meta">not notified</span>
                  }
                </span>
                <span>
                  @if (custodian.acknowledged) {
                    <span class="dv-chip dv-chip--upper dv-chip--ok">{{
                      custodian.acknowledged_at
                        ? formatDate(custodian.acknowledged_at)
                        : 'acknowledged'
                    }}</span>
                  } @else {
                    <span class="dv-chip dv-chip--upper dv-chip--warn">pending</span>
                  }
                </span>
                <span class="dv-muted dv-clip lhd-notes" [title]="custodian.notes">{{
                  custodian.notes
                }}</span>
              </div>
            }
          }
        }
      </div>
    </div>
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

  /** Console status chip modifier: an active hold is the dangerous state. */
  getStatusBadgeClass(status: LegalHold['status']): string {
    switch (status) {
      case 'active':
        return 'dv-chip--danger';
      case 'draft':
        return 'dv-chip--accent';
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
