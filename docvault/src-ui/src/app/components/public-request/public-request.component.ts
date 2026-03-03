import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PublicRequestInfo } from '../../models/portal.model';

@Component({
  selector: 'app-public-request',
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
    } @else if (request()) {
      <div style="min-height: 100vh; background: #f8f9fa;">
        <!-- Header -->
        <div class="py-4 bg-primary text-white">
          <div class="container text-center">
            <h2 class="mb-1">Document Request</h2>
            <p class="mb-0 opacity-75">{{ request()!.portal_name }}</p>
          </div>
        </div>

        <div class="container py-4" style="max-width: 640px;">
          <!-- Request Info -->
          <div class="card mb-4">
            <div class="card-body">
              <h5>{{ request()!.title }}</h5>
              @if (request()!.description) {
                <p style="white-space: pre-wrap;">{{ request()!.description }}</p>
              }
              @if (request()!.deadline) {
                <div class="d-flex align-items-center gap-2">
                  <i class="bi bi-calendar-event text-muted"></i>
                  <span>
                    Deadline: <strong>{{ request()!.deadline | date: 'mediumDate' }}</strong>
                  </span>
                  @if (daysRemaining() !== null) {
                    <span
                      class="badge"
                      [ngClass]="daysRemaining()! <= 0 ? 'bg-danger' : daysRemaining()! <= 3 ? 'bg-warning text-dark' : 'bg-success'"
                    >
                      @if (daysRemaining()! <= 0) {
                        Overdue
                      } @else if (daysRemaining() === 1) {
                        1 day left
                      } @else {
                        {{ daysRemaining() }} days left
                      }
                    </span>
                  }
                </div>
              }
            </div>
          </div>

          <!-- Success -->
          @if (uploadSuccess()) {
            <div class="alert alert-success">
              <i class="bi bi-check-circle me-2"></i>
              Your document has been uploaded successfully. Thank you!
            </div>
          } @else {
            <!-- Upload Form -->
            <div class="card">
              <div class="card-header">
                <i class="bi bi-cloud-upload me-1"></i>Upload Your Document
              </div>
              <div class="card-body">
                <div class="mb-3">
                  <label class="form-label">Your Name</label>
                  <input
                    type="text"
                    class="form-control"
                    [ngModel]="submitterName()"
                    (ngModelChange)="submitterName.set($event)"
                  />
                </div>
                <div class="mb-3">
                  <label class="form-label">Your Email</label>
                  <input
                    type="email"
                    class="form-control"
                    [ngModel]="submitterEmail()"
                    (ngModelChange)="submitterEmail.set($event)"
                  />
                </div>
                <div class="mb-3">
                  <label class="form-label">File <span class="text-danger">*</span></label>
                  <input
                    type="file"
                    class="form-control"
                    (change)="onFileSelected($event)"
                  />
                </div>

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
export class PublicRequestComponent implements OnInit {
  request = signal<PublicRequestInfo | null>(null);
  loading = signal(true);
  errorMsg = signal('');
  daysRemaining = signal<number | null>(null);

  submitterName = signal('');
  submitterEmail = signal('');
  selectedFile = signal<File | null>(null);
  uploading = signal(false);
  uploadProgress = signal(0);
  uploadError = signal('');
  uploadSuccess = signal(false);

  private token = '';

  constructor(
    private route: ActivatedRoute,
    private portalService: PortalService,
  ) {}

  ngOnInit(): void {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    this.loadRequest();
  }

  loadRequest(): void {
    this.loading.set(true);
    this.portalService.getPublicRequest(this.token).subscribe({
      next: (info) => {
        this.request.set(info);
        this.computeDeadline(info);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMsg.set(
          err.status === 404
            ? 'Request not found or has expired.'
            : 'Unable to load request information.',
        );
        this.loading.set(false);
      },
    });
  }

  private computeDeadline(info: PublicRequestInfo): void {
    if (!info.deadline) {
      this.daysRemaining.set(null);
      return;
    }
    const deadline = new Date(info.deadline);
    const now = new Date();
    const diffMs = deadline.getTime() - now.getTime();
    this.daysRemaining.set(Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile.set(input.files[0]);
    }
  }

  upload(): void {
    const file = this.selectedFile();
    if (!file) return;

    this.uploading.set(true);
    this.uploadError.set('');
    this.uploadProgress.set(0);

    const formData = new FormData();
    formData.append('file', file);
    if (this.submitterEmail()) formData.append('submitter_email', this.submitterEmail());
    if (this.submitterName()) formData.append('submitter_name', this.submitterName());

    this.portalService.publicRequestUpload(this.token, formData).subscribe({
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
