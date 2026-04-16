import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { CollaborationService } from '../../services/collaboration.service';
import { PublicShareAccess } from '../../models/collaboration.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-public-share',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container py-5" style="max-width: 600px;">
      <div class="text-center mb-4">
        <h4><i class="bi bi-file-earmark-text me-2"></i>DocVault</h4>
        <p class="text-muted">Shared Document</p>
      </div>

      @if (loading()) {
        <div class="text-center py-5">
          <div class="spinner-border"></div>
          <p class="text-muted mt-2">Loading shared document...</p>
        </div>
      } @else if (error()) {
        <div class="card">
          <div class="card-body text-center py-5">
            <i class="bi bi-exclamation-triangle text-warning" style="font-size: 3rem;"></i>
            <p class="mt-3">{{ error() }}</p>
          </div>
        </div>
      } @else if (requiresPassword()) {
        <div class="card">
          <div class="card-header">
            <h6 class="mb-0"><i class="bi bi-lock me-1"></i> Password Required</h6>
          </div>
          <div class="card-body">
            <p class="text-muted">This shared document is password-protected.</p>
            @if (passwordError()) {
              <div class="alert alert-danger py-2">{{ passwordError() }}</div>
            }
            <div class="mb-3">
              <label class="form-label">Password</label>
              <input
                type="password"
                class="form-control"
                [ngModel]="password()"
                (ngModelChange)="password.set($event)"
                (keyup.enter)="submitPassword()"
                placeholder="Enter password"
              />
            </div>
            <button
              class="btn btn-primary"
              (click)="submitPassword()"
              [disabled]="verifying() || !password()"
            >
              @if (verifying()) {
                <span class="spinner-border spinner-border-sm me-1"></span>
              }
              Access Document
            </button>
          </div>
        </div>
      } @else if (shareData()) {
        <div class="card">
          <div class="card-header">
            <h6 class="mb-0"><i class="bi bi-file-earmark me-1"></i> {{ shareData()!.document_title }}</h6>
          </div>
          <div class="card-body">
            <dl class="row mb-3">
              @if (shareData()!.file_version) {
                <dt class="col-sm-4">Version</dt>
                <dd class="col-sm-8">{{ shareData()!.file_version }}</dd>
              }
              @if (shareData()!.download_count !== undefined) {
                <dt class="col-sm-4">Downloads</dt>
                <dd class="col-sm-8">{{ shareData()!.download_count }}</dd>
              }
            </dl>
            <a
              class="btn btn-primary"
              [href]="getDownloadUrl()"
              target="_blank"
            >
              <i class="bi bi-download me-1"></i> Download
            </a>
          </div>
        </div>
      }
    </div>
  `,
})
export class PublicShareComponent implements OnInit {
  slug = '';
  loading = signal(false);
  error = signal('');
  requiresPassword = signal(false);
  password = signal('');
  passwordError = signal('');
  verifying = signal(false);
  shareData = signal<PublicShareAccess | null>(null);

  constructor(
    private route: ActivatedRoute,
    private collaborationService: CollaborationService,
  ) {}

  ngOnInit(): void {
    this.slug = this.route.snapshot.params['slug'];
    this.loadShare();
  }

  loadShare(): void {
    this.loading.set(true);
    this.error.set('');
    this.collaborationService.accessShareLink(this.slug).subscribe({
      next: (data) => {
        if (data.requires_password) {
          this.requiresPassword.set(true);
        } else {
          this.shareData.set(data);
        }
        this.loading.set(false);
      },
      error: (err) => {
        if (err.status === 404) {
          this.error.set('This share link is invalid or has expired.');
        } else {
          this.error.set('Unable to load shared document. Please try again later.');
        }
        this.loading.set(false);
      },
    });
  }

  submitPassword(): void {
    this.verifying.set(true);
    this.passwordError.set('');
    this.collaborationService.verifySharePassword(this.slug, this.password()).subscribe({
      next: (data) => {
        this.requiresPassword.set(false);
        this.shareData.set(data);
        this.verifying.set(false);
      },
      error: (err) => {
        if (err.status === 403) {
          this.passwordError.set('Incorrect password.');
        } else {
          this.passwordError.set('Verification failed. Please try again.');
        }
        this.verifying.set(false);
      },
    });
  }

  getDownloadUrl(): string {
    const docId = this.shareData()?.document_id;
    if (docId) {
      return `${environment.apiUrl}/documents/${docId}/download/`;
    }
    return '#';
  }
}
