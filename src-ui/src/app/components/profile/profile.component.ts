import { Component, OnInit, computed, signal } from '@angular/core';
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
  styleUrl: './profile.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading profile…</div>
        } @else if (user(); as u) {
          <div class="pf-head">
            <span class="dv-avatar dv-avatar--lg">{{ initials() }}</span>
            <div>
              <h1 class="dv-h1 dv-h1--sm pf-head__name">{{ u.username }}</h1>
              <div class="dv-meta">
                {{ u.email || 'no email' }} · {{ role() }} · joined
                {{ formatDate(u.date_joined) }}
              </div>
            </div>
            <button
              type="button"
              class="dv-btn dv-btn--danger dv-push"
              (click)="signOut()"
              [disabled]="signingOut()"
            >
              Sign out
            </button>
          </div>

          <div class="pf-grid">
            <div class="pf-col">
              <!-- Security -->
              <div class="dv-card dv-card--pad">
                <div class="dv-card__title">Security</div>
                <div class="pf-lines">
                  <div class="dv-stat-line">
                    <span class="dv-stat-line__k">two-factor</span>
                    <span class="dv-stat-line__v" [class.dv-ok]="otpStatus()?.enabled">
                      {{ otpStatus()?.enabled ? '✓ totp enabled' : 'not configured' }}
                    </span>
                  </div>
                  <div class="dv-stat-line">
                    <span class="dv-stat-line__k">account</span>
                    <span class="dv-stat-line__v" [class.dv-ok]="u.is_active">
                      {{ u.is_active ? '✓ active' : 'inactive' }}
                    </span>
                  </div>
                </div>
                <div class="pf-actions">
                  <a class="dv-btn dv-btn--ghost dv-btn--md" routerLink="/otp-setup">
                    {{ otpStatus()?.enabled ? 'Manage 2FA' : 'Set up 2FA' }}
                  </a>
                </div>
              </div>

              <!-- Change password -->
              <div class="dv-card dv-card--pad">
                <div class="dv-card__title">Change password</div>

                @if (passwordSuccess()) {
                  <div class="pf-banner pf-banner--ok" role="status">
                    <span>Password changed.</span>
                    <button
                      type="button"
                      class="pf-banner__close"
                      aria-label="Dismiss"
                      (click)="passwordSuccess.set(false)"
                    >
                      ✕
                    </button>
                  </div>
                }
                @if (passwordError()) {
                  <div class="pf-banner pf-banner--error" role="alert">
                    <span>{{ passwordError() }}</span>
                    <button
                      type="button"
                      class="pf-banner__close"
                      aria-label="Dismiss"
                      (click)="passwordError.set('')"
                    >
                      ✕
                    </button>
                  </div>
                }

                <div class="pf-form">
                  <div>
                    <label class="dv-field__label" for="pf-old">current password</label>
                    <input
                      id="pf-old"
                      type="password"
                      class="dv-input dv-input--mono"
                      autocomplete="current-password"
                      [ngModel]="oldPassword()"
                      (ngModelChange)="oldPassword.set($event)"
                    />
                  </div>
                  <div>
                    <label class="dv-field__label" for="pf-new">new password</label>
                    <input
                      id="pf-new"
                      type="password"
                      class="dv-input dv-input--mono"
                      autocomplete="new-password"
                      [ngModel]="newPassword()"
                      (ngModelChange)="newPassword.set($event)"
                    />
                  </div>
                  <button
                    type="button"
                    class="dv-btn dv-btn--primary dv-btn--md"
                    (click)="changePassword()"
                    [disabled]="changingPassword() || !oldPassword() || !newPassword()"
                  >
                    @if (changingPassword()) {
                      <span class="dv-spinner"></span>
                    }
                    Change password
                  </button>
                </div>
              </div>
            </div>

            <div class="pf-col">
              <!-- Account -->
              <div class="dv-card dv-card--pad">
                <div class="dv-card__title">Account</div>
                <div class="dv-kv pf-kv">
                  <span class="dv-kv__k">username</span>
                  <span class="dv-mono">{{ u.username }}</span>
                  <span class="dv-kv__k">email</span>
                  <span class="dv-mono">{{ u.email || '—' }}</span>
                  <span class="dv-kv__k">first name</span>
                  <span>{{ u.first_name || '—' }}</span>
                  <span class="dv-kv__k">last name</span>
                  <span>{{ u.last_name || '—' }}</span>
                  <span class="dv-kv__k">joined</span>
                  <span class="dv-mono">{{ formatDate(u.date_joined) }}</span>
                  <span class="dv-kv__k">status</span>
                  <span class="pf-chips">
                    @if (u.is_superuser) {
                      <span class="dv-chip dv-chip--accent">superuser</span>
                    } @else if (u.is_staff) {
                      <span class="dv-chip dv-chip--accent">staff</span>
                    }
                    <span class="dv-chip" [class.dv-chip--ok]="u.is_active">
                      {{ u.is_active ? 'active' : 'inactive' }}
                    </span>
                  </span>
                </div>
              </div>

              <!-- Notifications -->
              <div class="dv-card dv-card--pad">
                <div class="dv-card__title">Notifications</div>
                <div class="pf-lines">
                  <span class="dv-muted pf-prose">
                    Per-event delivery over in-app, email and webhook, plus your storage and
                    document quotas.
                  </span>
                  <a class="pf-link" routerLink="/notification-preferences">
                    notification preferences →
                  </a>
                </div>
              </div>
            </div>
          </div>
        }
      </div>
    </div>
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
  signingOut = signal(false);

  /** Two-letter avatar label, matching the rail avatar chip. */
  readonly initials = computed(() => {
    const u = this.user();
    if (!u) return '';
    const first = u.first_name?.trim();
    const last = u.last_name?.trim();
    if (first && last) return (first[0] + last[0]).toLowerCase();
    return u.username.slice(0, 2).toLowerCase();
  });

  /** Mono role readout under the username. */
  readonly role = computed(() => {
    const u = this.user();
    if (!u) return '';
    if (u.is_superuser) return 'superuser';
    if (u.is_staff) return 'staff';
    return 'user';
  });

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

  /** Ends the session; `clearAuth()` also redirects to the login screen. */
  signOut(): void {
    this.signingOut.set(true);
    this.authService.logout().subscribe({
      next: () => this.signingOut.set(false),
      error: () => {
        // The token is gone locally either way — drop it and bounce to login.
        this.authService.clearAuth();
        this.signingOut.set(false);
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
