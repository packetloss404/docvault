import { Component, Input, OnChanges, OnDestroy, SimpleChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SecurityService } from '../../services/security.service';
import { Signature } from '../../models/security.model';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-document-signatures',
  standalone: true,
  imports: [CommonModule],
  styleUrl: './document-signatures.component.scss',
  template: `
    <div class="dv-card dv-card--r10">
      <div class="dv-card__head">
        <span class="dv-card__title">Signatures</span>
        <div class="ds-actions dv-push">
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--sm"
            (click)="signDocument()"
            [disabled]="signing()"
          >
            @if (signing()) {
              <span class="dv-spinner"></span>
            }
            Sign
          </button>
          <button
            type="button"
            class="dv-btn dv-btn--ghost dv-btn--sm"
            (click)="verifyAll()"
            [disabled]="verifying()"
          >
            @if (verifying()) {
              <span class="dv-spinner"></span>
            }
            Verify all
          </button>
        </div>
      </div>

      <div class="ds-body">
        @if (errorMessage()) {
          <div class="dv-banner dv-banner--error" role="alert">
            <span>{{ errorMessage() }}</span>
            <button
              type="button"
              class="dv-banner__close"
              aria-label="Dismiss"
              (click)="errorMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        @if (successMessage()) {
          <div class="dv-banner dv-banner--ok" role="status">
            <span>{{ successMessage() }}</span>
            <button
              type="button"
              class="dv-banner__close"
              aria-label="Dismiss"
              (click)="successMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span></div>
        } @else if (signatures().length === 0) {
          <div class="dv-meta">No signatures on this document.</div>
        } @else {
          <div class="ds-list">
            @for (sig of signatures(); track sig.id) {
              <div class="ds-sig">
                <div class="ds-sig__main">
                  <div class="ds-sig__who">{{ sig.signer_username }}</div>
                  <div class="dv-meta">{{ sig.key_id }} · {{ sig.algorithm }}</div>
                  <div class="dv-meta">signed {{ formatDate(sig.created_at) }}</div>
                  @if (sig.verified_at) {
                    <div class="dv-meta dv-ok">verified {{ formatDate(sig.verified_at) }}</div>
                  }
                </div>
                <span
                  class="dv-chip dv-chip--upper"
                  [class.dv-chip--ok]="sig.verified"
                  [class.dv-chip--warn]="!sig.verified"
                  >{{ sig.verified ? 'verified' : 'unverified' }}</span
                >
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class DocumentSignaturesComponent implements OnChanges, OnDestroy {
  @Input() documentId!: number;
  @Input() documentChecksum = '';
  private signatureRequest?: Subscription;

  signatures = signal<Signature[]>([]);
  loading = signal(false);
  signing = signal(false);
  verifying = signal(false);
  errorMessage = signal('');
  successMessage = signal('');

  constructor(private securityService: SecurityService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['documentId'] || changes['documentChecksum']) {
      this.signatures.set([]);
      this.successMessage.set('');
      this.errorMessage.set('');
      this.loadSignatures();
    }
  }

  ngOnDestroy(): void {
    this.signatureRequest?.unsubscribe();
  }

  loadSignatures(): void {
    if (!this.documentId) return;
    this.signatureRequest?.unsubscribe();
    this.loading.set(true);
    this.signatureRequest = this.securityService.getDocumentSignatures(this.documentId).subscribe({
      next: (sigs) => {
        this.signatures.set(sigs);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  signDocument(): void {
    this.signing.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    this.securityService.signDocument(this.documentId).subscribe({
      next: () => {
        this.successMessage.set('Document signed successfully.');
        this.signing.set(false);
        this.loadSignatures();
      },
      error: () => {
        this.errorMessage.set('Failed to sign document. Check that you have a valid GPG key configured and that you have permission to sign this document.');
        this.signing.set(false);
      },
    });
  }

  verifyAll(): void {
    this.verifying.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    this.securityService.verifyDocumentSignatures(this.documentId).subscribe({
      next: (res) => {
        const allValid = res.results.every((r) => r.valid);
        const errors = res.results.filter((r) => !r.valid);
        if (allValid) {
          this.successMessage.set('All signatures verified successfully.');
        } else {
          this.errorMessage.set(
            `${errors.length} signature(s) could not be verified.`,
          );
        }
        this.loadSignatures();
        this.verifying.set(false);
      },
      error: () => {
        this.errorMessage.set('Signature verification failed. The GPG public key may be missing or the document may have been modified after signing.');
        this.verifying.set(false);
      },
    });
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
