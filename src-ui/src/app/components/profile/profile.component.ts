import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { SecurityService } from '../../services/security.service';
import { User } from '../../models/user.model';
import { OTPStatus } from '../../models/security.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <h3 class="mb-3">Profile</h3>

    @if (loading()) {
      <div class="text-center py-5">
        <div class="spinner-border"></div>
      </div>
    } @else if (user()) {
      <div class="row">
        <!-- Profile Info -->
        <div class="col-md-6 mb-4">
          <div class="card">
            <div class="card-header">
              <h6 class="mb-0"><i class="bi bi-person me-1"></i> Account Information</h6>
            </div>
            <div class="card-body">
              <dl class="row mb-0">
                <dt class="col-sm-4">Username</dt>
                <dd class="col-sm-8">{{ user()!.username }}</dd>
                <dt class="col-sm-4">Email</dt>
                <dd class="col-sm-8">{{ user()!.email || '—' }}</dd>
                <dt class="col-sm-4">First Name</dt>
                <dd class="col-sm-8">{{ user()!.first_name || '—' }}</dd>
                <dt class="col-sm-4">Last Name</dt>
                <dd class="col-sm-8">{{ user()!.last_name || '—' }}</dd>
                <dt class="col-sm-4">Joined</dt>
                <dd class="col-sm-8">{{ formatDate(user()!.date_joined) }}</dd>
                <dt class="col-sm-4">Status</dt>
                <dd class="col-sm-8">
                  @if (user()!.is_staff) {
                    <span class="badge bg-primary me-1">Staff</span>
                  }
                  <span class="badge" [class.bg-success]="user()!.is_active" [class.bg-secondary]="!user()!.is_active">
                    {{ user()!.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <!-- Security -->
        <div class="col-md-6 mb-4">
          <div class="card mb-3">
            <div class="card-header">
              <h6 class="mb-0"><i class="bi bi-shield-lock me-1"></i> Security</h6>
            </div>
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                  <strong>Two-Factor Authentication</strong>
                  <br />
                  <small class="text-muted">
                    @if (otpStatus()?.enabled) {
                      Enabled and active
                    } @else {
                      Not configured
                    }
                  </small>
                </div>
                <a routerLink="/otp-setup" class="btn btn-sm btn-outline-primary">
                  {{ otpStatus()?.enabled ? 'Manage' : 'Set Up' }}
                </a>
              </div>
            </div>
          </div>

          <!-- Change Password -->
          <div class="card">
            <div class="card-header">
              <h6 class="mb-0"><i class="bi bi-key me-1"></i> Change Password</h6>
            </div>
            <div class="card-body">
              @if (passwordSuccess()) {
                <div class="alert alert-success py-2">
                  Password changed successfully.
                  <button type="button" class="btn-close btn-close-sm float-end" (click)="passwordSuccess.set(false)"></button>
                </div>
              }
              @if (passwordError()) {
                <div class="alert alert-danger py-2">
                  {{ passwordError() }}
                  <button type="button" class="btn-close btn-close-sm float-end" (click)="passwordError.set('')"></button>
                </div>
              }
              <div class="mb-3">
                <label class="form-label">Current Password</label>
                <input
                  type="password"
                  class="form-control"
                  [ngModel]="oldPassword()"
                  (ngModelChange)="oldPassword.set($event)"
                />
              </div>
              <div class="mb-3">
                <label class="form-label">New Password</label>
                <input
                  type="password"
                  class="form-control"
                  [ngModel]="newPassword()"
                  (ngModelChange)="newPassword.set($event)"
                />
              </div>
              <button
                class="btn btn-primary btn-sm"
                (click)="changePassword()"
                [disabled]="changingPassword() || !oldPassword() || !newPassword()"
              >
                @if (changingPassword()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                }
                Change Password
              </button>
            </div>
          </div>
        </div>
      </div>
    }
  `,
})
export class ProfileComponent implements OnInit {
  user = signal<User | null>(null);
  otpStatus = signal<OTPStatus | null>(null);
  loading = signal(false);
  oldPassword = signal('');
  newPassword = signal('');
  changingPassword = signal(false);
  passwordSuccess = signal(false);
  passwordError = signal('');

  constructor(
    private authService: AuthService,
    private securityService: SecurityService,
  ) {}

  ngOnInit(): void {
    this.loading.set(true);
    this.authService.getProfile().subscribe({
      next: (user) => {
        this.user.set(user);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.securityService.getOTPStatus().subscribe({
      next: (status) => this.otpStatus.set(status),
    });
  }

  changePassword(): void {
    this.changingPassword.set(true);
    this.passwordSuccess.set(false);
    this.passwordError.set('');
    this.authService
      .changePassword({
        old_password: this.oldPassword(),
        new_password: this.newPassword(),
      })
      .subscribe({
        next: () => {
          this.passwordSuccess.set(true);
          this.oldPassword.set('');
          this.newPassword.set('');
          this.changingPassword.set(false);
        },
        error: () => {
          this.passwordError.set('Failed to change password. Check your current password and try again.');
          this.changingPassword.set(false);
        },
      });
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
}
