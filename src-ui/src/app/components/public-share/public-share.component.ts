import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { CollaborationService } from '../../services/collaboration.service';
import { PublicShareAccess } from '../../models/collaboration.model';

@Component({
  selector: 'app-public-share',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dv-auth">
      <div class="dv-auth__col" [class.ps__col--wide]="!!shareData()">
        <div class="dv-auth__brand">
          <div class="dv-auth__logo">V</div>
          <div>
            <div class="dv-auth__name">DocVault</div>
            <div class="dv-meta">shared document</div>
          </div>
        </div>

        @if (loading()) {
          <div class="dv-auth__card ps__state">
            <span class="dv-spinner"></span>
            <span class="dv-meta">loading shared document…</span>
          </div>
        } @else if (error()) {
          <div class="dv-auth__card ps__card" role="alert">
            <span class="dv-chip dv-chip--upper dv-chip--warn ps__badge">unavailable</span>
            <div class="ps__msg">{{ error() }}</div>
          </div>
        } @else if (requiresPassword()) {
          <div class="dv-auth__card">
            <span class="dv-chip dv-chip--upper ps__badge">password required</span>
            <div class="dv-meta">This shared document is password-protected.</div>

            @if (passwordError()) {
              <div class="ps__error" role="alert">{{ passwordError() }}</div>
            }

            <div>
              <label class="dv-field__label" for="ps-password">password</label>
              <input
                id="ps-password"
                type="password"
                class="dv-input dv-input--mono"
                autocomplete="current-password"
                [ngModel]="password()"
                (ngModelChange)="password.set($event)"
                (keyup.enter)="submitPassword()"
              />
            </div>

            <button
              type="button"
              class="dv-btn dv-btn--primary dv-btn--block"
              (click)="submitPassword()"
              [disabled]="verifying() || !password()"
            >
              @if (verifying()) {
                <span class="dv-spinner"></span>
                Checking…
              } @else {
                Access document →
              }
            </button>
          </div>
        } @else if (shareData()) {
          <div class="dv-auth__card ps__doc">
            <div class="ps__preview">
              <div class="dv-page ps__page">
                <span class="dv-meta">preview unavailable</span>
              </div>
            </div>

            <div class="ps__detail">
              <h1 class="dv-h2 ps__title">{{ shareData()!.document_title }}</h1>

              <div class="dv-kv ps__kv">
                @if (shareData()!.file_version) {
                  <span class="dv-kv__k">version</span>
                  <span class="dv-mono">{{ shareData()!.file_version }}</span>
                }
                @if (shareData()!.download_count !== undefined) {
                  <span class="dv-kv__k">downloads</span>
                  <span class="dv-mono">{{ shareData()!.download_count }}</span>
                }
              </div>

              <a
                class="dv-btn dv-btn--primary ps__download"
                [href]="getDownloadUrl()"
                target="_blank"
                rel="noopener"
              >
                ↓ Download
              </a>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styleUrl: './public-share.component.scss',
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
    const data = this.shareData();
    if (!data?.download_url) {
      return '#';
    }

    const token = data.download_token
      ? `?token=${encodeURIComponent(data.download_token)}`
      : '';
    return `${this.collaborationService.apiBaseUrl}${data.download_url.replace(/^\/api\/v1/, '')}${token}`;
  }
}
