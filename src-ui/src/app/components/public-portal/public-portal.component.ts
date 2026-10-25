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
    <div class="dv-auth">
      <div class="dv-auth__col pp__col">
        <div class="dv-auth__brand">
          @if (portal()?.logo) {
            <img class="pp__logo" [src]="portal()!.logo!" alt="" />
          } @else {
            <div class="dv-auth__logo">V</div>
          }
          <div>
            <div class="dv-auth__name">{{ portal()?.name || 'DocVault' }}</div>
            <div class="pp__sub">
              @if (portal()) {
                <!-- The portal's own brand colour, shown as a swatch rather
                     than themed across the page. -->
                <span
                  class="dv-dot dv-dot--xl pp__swatch"
                  [style.background]="portal()!.primary_color"
                  [title]="portal()!.primary_color"
                ></span>
              }
              <span class="dv-meta">document submission</span>
            </div>
          </div>
        </div>

        @if (loading()) {
          <div class="dv-auth__card pp__state">
            <span class="dv-spinner"></span>
            <span class="dv-meta">loading portal…</span>
          </div>
        } @else if (errorMsg()) {
          <div class="dv-auth__card" role="alert">
            <span class="dv-chip dv-chip--upper dv-chip--warn pp__badge">unavailable</span>
            <div class="pp__msg">{{ errorMsg() }}</div>
          </div>
        } @else if (portal()) {
          @if (portal()!.welcome_text) {
            <div class="dv-auth__card">
              <div class="pp__welcome">{{ portal()!.welcome_text }}</div>
            </div>
          }

          @if (uploadSuccess()) {
            <div class="dv-callout pp__done" role="status">
              <div class="dv-callout__label">uploaded</div>
              <div class="pp__msg">
                Your document has been uploaded. Thank you.
              </div>
            </div>
          } @else {
            <div class="dv-auth__card">
              <span class="dv-eyebrow">upload document</span>

              @if (portal()!.require_name) {
                <div>
                  <label class="dv-field__label" for="pp-name">
                    your name <span class="dv-danger">*</span>
                  </label>
                  <input
                    id="pp-name"
                    type="text"
                    class="dv-input"
                    autocomplete="name"
                    [ngModel]="submitterName()"
                    (ngModelChange)="submitterName.set($event)"
                  />
                </div>
              }

              @if (portal()!.require_email) {
                <div>
                  <label class="dv-field__label" for="pp-email">
                    your email <span class="dv-danger">*</span>
                  </label>
                  <input
                    id="pp-email"
                    type="email"
                    class="dv-input"
                    autocomplete="email"
                    [ngModel]="submitterEmail()"
                    (ngModelChange)="submitterEmail.set($event)"
                  />
                </div>
              }

              <div>
                <span class="dv-field__label">
                  file <span class="dv-danger">*</span>
                </span>
                <label class="dv-dropzone pp__drop">
                  <input
                    type="file"
                    class="pp__file"
                    (change)="onFileSelected($event)"
                  />
                  @if (selectedFile()) {
                    <span class="pp__filename dv-clip">{{
                      selectedFile()!.name
                    }}</span>
                    <span class="dv-meta">choose a different file</span>
                  } @else {
                    <span>Drop a file here, or click to choose</span>
                  }
                </label>
                <div class="dv-meta pp__limit">
                  max {{ portal()!.max_file_size_mb }} MB
                </div>
              </div>

              @if (fileError()) {
                <div class="pp__error" role="alert">{{ fileError() }}</div>
              }

              @if (uploading()) {
                <div>
                  <div class="dv-bar">
                    <div class="dv-bar__fill" [style.width.%]="uploadProgress()"></div>
                  </div>
                  <div class="dv-meta pp__pct">{{ uploadProgress() }}%</div>
                </div>
              }

              @if (uploadError()) {
                <div class="pp__error" role="alert">{{ uploadError() }}</div>
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
  styleUrl: './public-portal.component.scss',
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
    if (this.submitterEmail()) formData.append('email', this.submitterEmail());
    if (this.submitterName()) formData.append('name', this.submitterName());

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
