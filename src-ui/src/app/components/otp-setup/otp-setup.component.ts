import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { OTPSetupResponse } from '../../models/security.model';

@Component({
  selector: 'app-otp-setup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container-fluid py-4">
      <h4>Two-Factor Authentication</h4>

      @if (loading()) {
        <div class="text-center py-4">
          <div class="spinner-border"></div>
        </div>
      } @else {

        @if (errorMessage()) {
          <div class="alert alert-danger alert-dismissible">
            {{ errorMessage() }}
            <button type="button" class="btn-close" (click)="errorMessage.set('')"></button>
          </div>
        }

        @if (successMessage()) {
          <div class="alert alert-success alert-dismissible">
            {{ successMessage() }}
            <button type="button" class="btn-close" (click)="successMessage.set('')"></button>
          </div>
        }

        <!-- Status: OTP not enabled -->
        @if (!otpEnabled()) {
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">2FA is not enabled</h5>
              <p class="text-muted">
                Two-factor authentication adds an extra layer of security to your account.
                You will need a TOTP authenticator app (such as Google Authenticator or Authy).
              </p>
              <button class="btn btn-primary" (click)="enableOTP()" [disabled]="setupLoading()">
                @if (setupLoading()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                }
                Enable 2FA
              </button>
            </div>
          </div>
        }

        <!-- Step: Show QR Code -->
        @if (setupData()) {
          <div class="card mt-3">
            <div class="card-header">Setup Two-Factor Authentication</div>
            <div class="card-body">
              <p>Scan this QR code with your authenticator app:</p>
              <div class="text-center mb-3">
                <img [src]="'data:image/png;base64,' + setupData()!.qr_code_base64"
                     alt="QR Code" class="border rounded" style="max-width: 250px;" />
              </div>
              <div class="mb-3">
                <label class="form-label fw-bold">Secret Key (manual entry):</label>
                <div class="input-group" style="max-width: 400px;">
                  <input type="text" class="form-control font-monospace" [value]="setupData()!.secret" readonly />
                  <button class="btn btn-outline-secondary" (click)="copySecret()">
                    <i class="bi bi-clipboard"></i>
                  </button>
                </div>
              </div>
              <hr />
              <div class="mb-3" style="max-width: 300px;">
                <label class="form-label">Enter the 6-digit code from your app:</label>
                <input type="text" class="form-control" [(ngModel)]="confirmCode"
                       maxlength="6" placeholder="000000" />
              </div>
              <button class="btn btn-success" (click)="confirmOTP()" [disabled]="confirmLoading() || confirmCode.length < 6">
                @if (confirmLoading()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                }
                Verify &amp; Activate
              </button>
            </div>
          </div>
        }

        <!-- Step: Show Backup Codes -->
        @if (backupCodes().length > 0) {
          <div class="card mt-3 border-success">
            <div class="card-header bg-success text-white">
              <i class="bi bi-shield-check me-1"></i> 2FA Enabled Successfully
            </div>
            <div class="card-body">
              <p class="fw-bold">Save these backup codes in a secure location:</p>
              <p class="text-muted">Each code can only be used once. If you lose access to your authenticator, use one of these codes to log in.</p>
              <div class="row">
                @for (code of backupCodes(); track code) {
                  <div class="col-6 col-md-4 mb-2">
                    <code class="fs-5">{{ code }}</code>
                  </div>
                }
              </div>
              <button class="btn btn-outline-secondary mt-3" (click)="copyBackupCodes()">
                <i class="bi bi-clipboard me-1"></i> Copy All Codes
              </button>
            </div>
          </div>
        }

        <!-- Status: OTP enabled -->
        @if (otpEnabled() && !setupData() && backupCodes().length === 0) {
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">
                <i class="bi bi-shield-check text-success me-2"></i>
                2FA is enabled
              </h5>
              <p class="text-muted">
                Your account is protected with two-factor authentication.
              </p>
              <hr />
              <p class="mb-2">To disable 2FA, enter your password:</p>
              <div class="input-group mb-3" style="max-width: 400px;">
                <input type="password" class="form-control" [(ngModel)]="disablePassword"
                       placeholder="Current password" />
                <button class="btn btn-danger" (click)="disableOTP()"
                        [disabled]="disableLoading() || !disablePassword">
                  @if (disableLoading()) {
                    <span class="spinner-border spinner-border-sm me-1"></span>
                  }
                  Disable 2FA
                </button>
              </div>
            </div>
          </div>
        }

      }
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
