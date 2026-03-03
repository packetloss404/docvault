import { Component, Input, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SecurityService } from '../../services/security.service';
import { Signature } from '../../models/security.model';

@Component({
  selector: 'app-document-signatures',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0"><i class="bi bi-pen me-1"></i> Signatures</h6>
        <div>
          <button class="btn btn-sm btn-outline-primary me-1" (click)="signDocument()" [disabled]="signing()">
            @if (signing()) {
              <span class="spinner-border spinner-border-sm me-1"></span>
            }
            Sign
          </button>
          <button class="btn btn-sm btn-outline-success" (click)="verifyAll()" [disabled]="verifying()">
            @if (verifying()) {
              <span class="spinner-border spinner-border-sm me-1"></span>
            }
            Verify All
          </button>
        </div>
      </div>
      <div class="card-body">
        @if (errorMessage()) {
          <div class="alert alert-danger alert-dismissible py-2">
            {{ errorMessage() }}
            <button type="button" class="btn-close btn-close-sm" (click)="errorMessage.set('')"></button>
          </div>
        }

        @if (successMessage()) {
          <div class="alert alert-success alert-dismissible py-2">
            {{ successMessage() }}
            <button type="button" class="btn-close btn-close-sm" (click)="successMessage.set('')"></button>
          </div>
        }

        @if (loading()) {
          <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm"></div>
          </div>
        } @else if (signatures().length === 0) {
          <p class="text-muted mb-0 small">No signatures on this document.</p>
        } @else {
          <div class="list-group list-group-flush">
            @for (sig of signatures(); track sig.id) {
              <div class="list-group-item px-0">
                <div class="d-flex justify-content-between align-items-start">
                  <div>
                    <strong>{{ sig.signer_username }}</strong>
                    <br />
                    <small class="text-muted">
                      Key: {{ sig.key_id }} &middot; {{ sig.algorithm }}
                    </small>
                    <br />
                    <small class="text-muted">
                      Signed: {{ formatDate(sig.created_at) }}
                    </small>
                  </div>
                  <div>
                    @if (sig.verified) {
                      <span class="badge bg-success">
                        <i class="bi bi-check-circle me-1"></i> Verified
                      </span>
                    } @else {
                      <span class="badge bg-warning text-dark">
                        <i class="bi bi-question-circle me-1"></i> Unverified
                      </span>
                    }
                  </div>
                </div>
                @if (sig.verified_at) {
                  <small class="text-success">Verified at: {{ formatDate(sig.verified_at) }}</small>
                }
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class DocumentSignaturesComponent implements OnInit {
  @Input() documentId!: number;

  signatures = signal<Signature[]>([]);
  loading = signal(false);
  signing = signal(false);
  verifying = signal(false);
  errorMessage = signal('');
  successMessage = signal('');

  constructor(private securityService: SecurityService) {}

  ngOnInit(): void {
    this.loadSignatures();
  }

  loadSignatures(): void {
    this.loading.set(true);
    this.securityService.getDocumentSignatures(this.documentId).subscribe({
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
        this.errorMessage.set('Failed to sign document. Ensure you have a GPG key configured.');
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
        this.signatures.set(res.results);
        const allVerified = res.results.every((s) => s.verified);
        if (allVerified) {
          this.successMessage.set('All signatures verified successfully.');
        } else {
          this.errorMessage.set('Some signatures could not be verified.');
        }
        this.verifying.set(false);
      },
      error: () => {
        this.errorMessage.set('Verification failed.');
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
