import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { HttpEventType } from '@angular/common/http';
import { PortalService } from '../../services/portal.service';
import { PublicPortalInfo } from '../../models/portal.model';

@Component({
  selector: 'app-public-portal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (loading()) {
      <div class="d-flex justify-content-center align-items-center" style="min-height: 100vh;">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (errorMsg()) {
      <div class="d-flex justify-content-center align-items-center" style="min-height: 100vh;">
        <div class="text-center">
          <i class="bi bi-exclamation-triangle fs-1 text-warning"></i>
          <p class="mt-2">{{ errorMsg() }}</p>
        </div>
      </div>
    } @else if (portal()) {
      <div style="min-height: 100vh; background: #f8f9fa;">
        <!-- Header -->
        <div
          class="py-4 text-white"
          [style.background]="portal()!.primary_color"
        >
          <div class="container text-center">
            @if (portal()!.logo) {
              <img
                [src]="portal()!.logo!"
                alt="Portal Logo"
                style="max-height: 64px;"
                class="mb-2"
              />
            }
            <h2 class="mb-0">{{ portal()!.name }}</h2>
          </div>
        </div>

        <div class="container py-4" style="max-width: 640px;">
          <!-- Welcome Text -->
          @if (portal()!.welcome_text) {
            <div class="card mb-4">
              <div class="card-body">
                <p class="mb-0" style="white-space: pre-wrap;">{{ portal()!.welcome_text }}</p>
              </div>
            </div>
          }

          <!-- Success Message -->
          @if (uploadSuccess()) {
            <div class="alert alert-success">
              <i class="bi bi-check-circle me-2"></i>
              Your document has been uploaded successfully. Thank you!
            </div>
          } @else {
            <!-- Upload Form -->
            <div class="card">
              <div class="card-header">
                <i class="bi bi-cloud-upload me-1"></i>Upload Document
              </div>
              <div class="card-body">
                @if (portal()!.require_name) {
                  <div class="mb-3">
                    <label class="form-label">Your Name <span class="text-danger">*</span></label>
                    <input
                      type="text"
                      class="form-control"
                      [ngModel]="submitterName()"
                      (ngModelChange)="submitterName.set($event)"
                    />
                  </div>
                }
                @if (portal()!.require_email) {
                  <div class="mb-3">
                    <label class="form-label">Your Email <span class="text-danger">*</span></label>
                    <input
                      type="email"
                      class="form-control"
                      [ngModel]="submitterEmail()"
                      (ngModelChange)="submitterEmail.set($event)"
                    />
                  </div>
                }
                <div class="mb-3">
                  <label class="form-label">File <span class="text-danger">*</span></label>
                  <input
                    type="file"
                    class="form-control"
                    (change)="onFileSelected($event)"
                  />
                  <div class="form-text">
                    Maximum file size: {{ portal()!.max_file_size_mb }} MB
                  </div>
                </div>

                @if (fileError()) {
                  <div class="alert alert-danger py-2 small">{{ fileError() }}</div>
                }

                @if (uploading()) {
                  <div class="progress mb-3" style="height: 24px;">
                    <div
                      class="progress-bar progress-bar-striped progress-bar-animated"
                      role="progressbar"
                      [style.width.%]="uploadProgress()"
                    >
                      {{ uploadProgress() }}%
                    </div>
                  </div>
                }

                @if (uploadError()) {
                  <div class="alert alert-danger py-2">{{ uploadError() }}</div>
                }

                <button
                  class="btn btn-primary w-100"
                  [style.background]="portal()!.primary_color"
                  [style.borderColor]="portal()!.primary_color"
                  (click)="upload()"
                  [disabled]="uploading() || !selectedFile()"
                >
                  @if (uploading()) {
                    <span class="spinner-border spinner-border-sm me-1"></span>
                    Uploading...
                  } @else {
                    <i class="bi bi-cloud-upload me-1"></i>Upload
                  }
                </button>
              </div>
            </div>
          }
        </div>
      </div>
    }
  `,
})
export class PublicPortalComponent implements OnInit {
  portal = signal<PublicPortalInfo | null>(null);
  loading = signal(true);
  errorMsg = signal('');

  submitterName = signal('');
  submitterEmail = signal('');
  selectedFile = signal<File | null>(null);
  fileError = signal('');
  uploading = signal(false);
  uploadProgress = signal(0);
  uploadError = signal('');
  uploadSuccess = signal(false);

  private slug = '';

  constructor(
    private route: ActivatedRoute,
    private portalService: PortalService,
  ) {}

  ngOnInit(): void {
    this.slug = this.route.snapshot.paramMap.get('slug') || '';
    this.loadPortal();
  }

  loadPortal(): void {
    this.loading.set(true);
    this.portalService.getPublicPortal(this.slug).subscribe({
      next: (info) => {
        this.portal.set(info);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMsg.set(
          err.status === 404
            ? 'Portal not found.'
            : 'Unable to load portal information.',
        );
        this.loading.set(false);
      },
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.fileError.set('');
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      const maxBytes = (this.portal()?.max_file_size_mb || 25) * 1024 * 1024;
      if (file.size > maxBytes) {
        this.fileError.set(
          `File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds the maximum of ${this.portal()?.max_file_size_mb} MB.`,
        );
        this.selectedFile.set(null);
        return;
      }
      this.selectedFile.set(file);
    }
  }

  upload(): void {
    const file = this.selectedFile();
    if (!file) return;

    const p = this.portal();
    if (p?.require_email && !this.submitterEmail()) {
      this.uploadError.set('Email is required.');
      return;
    }
    if (p?.require_name && !this.submitterName()) {
      this.uploadError.set('Name is required.');
      return;
    }

    this.uploading.set(true);
    this.uploadError.set('');
    this.uploadProgress.set(0);

    const formData = new FormData();
    formData.append('file', file);
    if (this.submitterEmail()) formData.append('submitter_email', this.submitterEmail());
    if (this.submitterName()) formData.append('submitter_name', this.submitterName());

    this.portalService.publicUpload(this.slug, formData).subscribe({
      next: () => {
        this.uploading.set(false);
        this.uploadProgress.set(100);
        this.uploadSuccess.set(true);
      },
      error: (err) => {
        this.uploading.set(false);
        this.uploadError.set(
          err.error?.detail || 'Upload failed. Please try again.',
        );
      },
    });
  }
}
