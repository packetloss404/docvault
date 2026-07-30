import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  username = '';
  password = '';
  otpCode = '';
  otpRequired = false;
  errorMessage = '';
  loading = false;

  constructor(
    private auth: AuthService,
    private router: Router,
  ) {}

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
          this.otpCode = '';
          this.loading = false;
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
}
