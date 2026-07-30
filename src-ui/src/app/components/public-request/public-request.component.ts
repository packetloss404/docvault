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
    <div class="dv-auth">
      <div class="dv-auth__col pr__col">
        <div class="dv-auth__brand">
          <div class="dv-auth__logo">V</div>
          <div>
            <div class="dv-auth__name">DocVault</div>
            <div class="dv-meta">
              document request@if (request()) { · {{ request()!.portal_name }} }
            </div>
          </div>
        </div>

        @if (loading()) {
          <div class="dv-auth__card pr__state">
            <span class="dv-spinner"></span>
            <span class="dv-meta">loading request…</span>
          </div>
        } @else if (errorMsg()) {
          <div class="dv-auth__card" role="alert">
            <span class="dv-chip dv-chip--upper dv-chip--warn pr__badge">unavailable</span>
            <div class="pr__msg">{{ errorMsg() }}</div>
          </div>
        } @else if (request()) {
          <div class="dv-auth__card pr__brief">
            <h1 class="dv-h2">{{ request()!.title }}</h1>

            @if (request()!.description) {
              <div class="pr__desc">{{ request()!.description }}</div>
            }

            @if (request()!.deadline) {
              <div class="pr__deadline">
                <span class="dv-eyebrow">deadline</span>
                <span class="dv-mono pr__date">{{
                  request()!.deadline | date: 'yyyy-MM-dd'
                }}</span>
                @if (daysRemaining() !== null) {
                  <span
                    class="dv-chip dv-chip--upper"
                    [class.dv-chip--danger]="daysRemaining()! <= 0"
                    [class.dv-chip--warn]="
                      daysRemaining()! > 0 && daysRemaining()! <= 3
                    "
                    [class.dv-chip--ok]="daysRemaining()! > 3"
                  >
                    @if (daysRemaining()! <= 0) {
                      overdue
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

          @if (uploadSuccess()) {
            <div class="dv-callout pr__done" role="status">
              <div class="dv-callout__label">uploaded</div>
              <div class="pr__msg">
                Your document has been uploaded. Thank you.
              </div>
            </div>
          } @else {
            <div class="dv-auth__card">
              <span class="dv-eyebrow">upload your document</span>

              <div>
                <label class="dv-field__label" for="pr-name">your name</label>
                <input
                  id="pr-name"
                  type="text"
                  class="dv-input"
                  autocomplete="name"
                  [ngModel]="submitterName()"
                  (ngModelChange)="submitterName.set($event)"
                />
              </div>

              <div>
                <label class="dv-field__label" for="pr-email">your email</label>
                <input
                  id="pr-email"
                  type="email"
                  class="dv-input"
                  autocomplete="email"
                  [ngModel]="submitterEmail()"
                  (ngModelChange)="submitterEmail.set($event)"
                />
              </div>

              <div>
                <span class="dv-field__label">
                  file <span class="dv-danger">*</span>
                </span>
                <label class="dv-dropzone pr__drop">
                  <input
                    type="file"
                    class="pr__file"
                    (change)="onFileSelected($event)"
                  />
                  @if (selectedFile()) {
                    <span class="pr__filename dv-clip">{{
                      selectedFile()!.name
                    }}</span>
                    <span class="dv-meta">choose a different file</span>
                  } @else {
                    <span>Drop a file here, or click to choose</span>
                  }
                </label>
              </div>

              @if (uploading()) {
                <div>
                  <div class="dv-bar">
                    <div class="dv-bar__fill" [style.width.%]="uploadProgress()"></div>
                  </div>
                  <div class="dv-meta pr__pct">{{ uploadProgress() }}%</div>
                </div>
              }

              @if (uploadError()) {
                <div class="pr__error" role="alert">{{ uploadError() }}</div>
              }

              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--block"
                (click)="upload()"
                [disabled]="uploading() || !selectedFile()"
              >
                @if (uploading()) {
                  <span class="dv-spinner"></span>
                  Uploading…
                } @else {
                  Upload →
                }
              </button>
            </div>
          }
        }
      </div>
    </div>
  `,
  styleUrl: './public-request.component.scss',
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
