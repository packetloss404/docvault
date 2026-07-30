import { Component, ElementRef, ViewChildren, QueryList, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { environment } from '../../../environments/environment';

const OTP_LENGTH = 6;

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  @ViewChildren('otpBox') otpBoxes!: QueryList<ElementRef<HTMLInputElement>>;

  readonly version = environment.appVersion;

  username = '';
  password = '';
  otpCode = '';
  otpRequired = false;
  errorMessage = '';
  loading = false;

  /** One entry per box; `otpCode` is kept as the joined value. */
  otpDigits: string[] = Array(OTP_LENGTH).fill('');

  onSubmit(): void {
    this.errorMessage = '';
    this.loading = true;

    const credentials = {
      username: this.username,
      password: this.password,
      ...(this.otpRequired ? { otp_code: this.otpCode } : {}),
    };

    this.auth.login(credentials).subscribe({
      next: (res) => {
        if (res.otp_required) {
          this.otpRequired = true;
          this.resetOtp();
          this.loading = false;
          setTimeout(() => this.focusOtp(0), 0);
          return;
        }
        this.router.navigate(['/']);
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage =
          err.error?.non_field_errors?.[0] ||
          err.error?.otp_code?.[0] ||
          err.error?.detail ||
          'Login failed. Please check your credentials.';
      },
    });
  }

  onOtpInput(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const digit = input.value.replace(/\D/g, '').slice(-1);
    this.otpDigits[index] = digit;
    input.value = digit;
    this.syncOtpCode();

    if (digit && index < OTP_LENGTH - 1) {
      this.focusOtp(index + 1);
    } else if (this.otpCode.length === OTP_LENGTH) {
      this.onSubmit();
    }
  }

  onOtpKeydown(index: number, event: KeyboardEvent): void {
    if (event.key === 'Backspace') {
      // Clear this box first; a second press steps back into the previous one.
      if (this.otpDigits[index]) {
        this.otpDigits[index] = '';
        this.syncOtpCode();
        this.writeBox(index, '');
      } else if (index > 0) {
        event.preventDefault();
        this.otpDigits[index - 1] = '';
        this.syncOtpCode();
        this.writeBox(index - 1, '');
        this.focusOtp(index - 1);
      }
      return;
    }
    if (event.key === 'ArrowLeft' && index > 0) {
      event.preventDefault();
      this.focusOtp(index - 1);
    }
    if (event.key === 'ArrowRight' && index < OTP_LENGTH - 1) {
      event.preventDefault();
      this.focusOtp(index + 1);
    }
  }

  /** Lets a full code be pasted into any box. */
  onOtpPaste(event: ClipboardEvent): void {
    const pasted = event.clipboardData?.getData('text') ?? '';
    const digits = pasted.replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!digits) return;
    event.preventDefault();
    for (let i = 0; i < OTP_LENGTH; i++) {
      this.otpDigits[i] = digits[i] ?? '';
      this.writeBox(i, this.otpDigits[i]);
    }
    this.syncOtpCode();
    this.focusOtp(Math.min(digits.length, OTP_LENGTH - 1));
    if (this.otpCode.length === OTP_LENGTH) this.onSubmit();
  }

  private syncOtpCode(): void {
    this.otpCode = this.otpDigits.join('');
  }

  private resetOtp(): void {
    this.otpDigits = Array(OTP_LENGTH).fill('');
    this.otpCode = '';
  }

  private focusOtp(index: number): void {
    this.otpBoxes?.get(index)?.nativeElement.focus();
  }

  private writeBox(index: number, value: string): void {
    const box = this.otpBoxes?.get(index)?.nativeElement;
    if (box) box.value = value;
  }
}
