import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { OTPSetupResponse } from '../../models/security.model';

@Component({
  selector: 'app-otp-setup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  styleUrl: './otp-setup.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--narrow">
        <div class="dv-pagehead">
          <h1 class="dv-h1 dv-h1--sm">Two-factor authentication</h1>
          @if (otpEnabled()) {
            <span class="dv-chip dv-chip--ok dv-chip--upper">totp enabled</span>
          } @else {
            <span class="dv-chip dv-chip--upper">not configured</span>
          }
        </div>

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Reading 2FA status…</div>
        } @else {
          @if (errorMessage()) {
            <div class="ot-banner ot-banner--error" role="alert">
              <span>{{ errorMessage() }}</span>
              <button
                type="button"
                class="ot-banner__close"
                aria-label="Dismiss"
                (click)="errorMessage.set('')"
              >
                ✕
              </button>
            </div>
          }

          @if (successMessage()) {
            <div class="ot-banner ot-banner--ok" role="status">
              <span>{{ successMessage() }}</span>
              <button
                type="button"
                class="ot-banner__close"
                aria-label="Dismiss"
                (click)="successMessage.set('')"
              >
                ✕
              </button>
            </div>
          }

          <!-- Not enabled -->
          @if (!otpEnabled()) {
            <div class="dv-card dv-card--pad ot-card">
              <div class="dv-card__title">2FA is not enabled</div>
              <p class="ot-prose">
                Two-factor authentication adds a second step to sign-in. You will need a TOTP
                authenticator app such as Google Authenticator, Aegis or 1Password.
              </p>
              <div class="ot-actions">
                <button
                  type="button"
                  class="dv-btn dv-btn--primary dv-btn--md"
                  (click)="enableOTP()"
                  [disabled]="setupLoading()"
                >
                  @if (setupLoading()) {
                    <span class="dv-spinner"></span>
                  }
                  Enable 2FA
                </button>
              </div>
            </div>
          }

          <!-- Enrolment: QR + secret + confirmation -->
          @if (setupData(); as setup) {
            <div class="dv-card dv-card--pad dv-card--accent ot-card">
              <div class="dv-card__title">Scan with your authenticator</div>

              <div class="ot-qr">
                <img
                  [src]="'data:image/png;base64,' + setup.qr_code_base64"
                  alt="TOTP enrolment QR code"
                />
              </div>

              <div class="ot-field">
                <label class="dv-field__label" for="ot-secret">secret (manual entry)</label>
                <div class="ot-inline">
                  <input
                    id="ot-secret"
                    type="text"
                    class="dv-input dv-input--mono"
                    [value]="setup.secret"
                    readonly
                  />
                  <button
                    type="button"
                    class="dv-btn dv-btn--ghost dv-btn--sm"
                    title="Copy secret"
                    (click)="copySecret()"
                  >
                    ⧉
                  </button>
                </div>
              </div>

              <hr class="dv-divider ot-field" />

              <div class="ot-field">
                <label class="dv-field__label" for="ot-code">6-digit code from your app</label>
                <input
                  id="ot-code"
                  type="text"
                  class="dv-input dv-input--mono ot-code"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  placeholder="000000"
                  [(ngModel)]="confirmCode"
                />
              </div>

              <div class="ot-actions">
                <button
                  type="button"
                  class="dv-btn dv-btn--primary dv-btn--md"
                  (click)="confirmOTP()"
                  [disabled]="confirmLoading() || confirmCode.length < 6"
                >
                  @if (confirmLoading()) {
                    <span class="dv-spinner"></span>
                  }
                  Verify &amp; activate →
                </button>
              </div>
            </div>
          }

          <!-- Backup codes -->
          @if (backupCodes().length > 0) {
            <div class="dv-card dv-card--pad ot-card">
              <div class="dv-card__title dv-ok">✓ 2FA enabled</div>
              <p class="ot-prose">
                Save these backup codes somewhere safe. Each one works once, and they are the only
                way in if you lose your authenticator.
              </p>
              <div class="dv-well ot-codes">
                @for (code of backupCodes(); track code) {
                  <code>{{ code }}</code>
                }
              </div>
              <div class="ot-actions">
                <button
                  type="button"
                  class="dv-btn dv-btn--ghost dv-btn--md"
                  (click)="copyBackupCodes()"
                >
                  ⧉ Copy all codes
                </button>
              </div>
            </div>
          }

          <!-- Enabled -->
          @if (otpEnabled() && !setupData() && backupCodes().length === 0) {
            <div class="dv-card dv-card--pad ot-card">
              <div class="dv-card__title">2FA is active</div>
              <p class="ot-prose">
                Sign-in requires a code from your authenticator app. Disabling 2FA needs your
                current password.
              </p>

              <div class="ot-field">
                <label class="dv-field__label" for="ot-disable">current password</label>
                <div class="ot-inline">
                  <input
                    id="ot-disable"
                    type="password"
                    class="dv-input dv-input--mono"
                    autocomplete="current-password"
                    placeholder="Current password"
                    [(ngModel)]="disablePassword"
                  />
                  <button
                    type="button"
                    class="dv-btn dv-btn--danger dv-btn--md"
                    (click)="disableOTP()"
                    [disabled]="disableLoading() || !disablePassword"
                  >
                    @if (disableLoading()) {
                      <span class="dv-spinner"></span>
                    }
                    Disable 2FA
                  </button>
                </div>
              </div>
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class OTPSetupComponent implements OnInit {
  loading = signal(true);
  otpEnabled = signal(false);
  setupLoading = signal(false);
  confirmLoading = signal(false);
  disableLoading = signal(false);
  setupData = signal<OTPSetupResponse | null>(null);
  backupCodes = signal<string[]>([]);
  errorMessage = signal('');
  successMessage = signal('');

  confirmCode = '';
  disablePassword = '';

  constructor(private securityService: SecurityService) {}

  ngOnInit(): void {
    this.loadStatus();
  }

  loadStatus(): void {
    this.loading.set(true);
    this.securityService.getOTPStatus().subscribe({
      next: (status) => {
        this.otpEnabled.set(status.enabled && status.confirmed);
        this.loading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to load OTP status.');
        this.loading.set(false);
      },
    });
  }

  enableOTP(): void {
    this.setupLoading.set(true);
    this.errorMessage.set('');
    this.securityService.setupOTP().subscribe({
      next: (data) => {
        this.setupData.set(data);
        this.setupLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to initialize OTP setup.');
        this.setupLoading.set(false);
      },
    });
  }

  confirmOTP(): void {
    this.confirmLoading.set(true);
    this.errorMessage.set('');
    this.securityService.confirmOTP(this.confirmCode).subscribe({
      next: (res) => {
        this.backupCodes.set(res.backup_codes);
        this.setupData.set(null);
        this.otpEnabled.set(true);
        this.confirmCode = '';
        this.confirmLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Invalid verification code. Please try again.');
        this.confirmLoading.set(false);
      },
    });
  }

  disableOTP(): void {
    this.disableLoading.set(true);
    this.errorMessage.set('');
    this.securityService.disableOTP(this.disablePassword).subscribe({
      next: () => {
        this.otpEnabled.set(false);
        this.disablePassword = '';
        this.successMessage.set('Two-factor authentication has been disabled.');
        this.disableLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Incorrect password. Could not disable 2FA.');
        this.disableLoading.set(false);
      },
    });
  }

  copySecret(): void {
    const data = this.setupData();
    if (data) {
      navigator.clipboard.writeText(data.secret);
    }
  }

  copyBackupCodes(): void {
    const codes = this.backupCodes().join('\n');
    navigator.clipboard.writeText(codes);
  }
}
