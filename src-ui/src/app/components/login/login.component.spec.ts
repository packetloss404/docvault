import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Observable, Subject, of, throwError } from 'rxjs';

import { LoginComponent } from './login.component';
import { AuthService } from '../../services/auth.service';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let mockAuthService: { login: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockAuthService = {
      login: vi.fn().mockReturnValue(of({ token: 'fake-token', username: 'user' })),
    };

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: mockAuthService },
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have empty initial state', () => {
    expect(component.username).toBe('');
    expect(component.password).toBe('');
    expect(component.otpCode).toBe('');
    expect(component.otpRequired).toBe(false);
    expect(component.errorMessage).toBe('');
    expect(component.loading).toBe(false);
  });

  it('should call auth.login with credentials on submit', () => {
    component.username = 'testuser';
    component.password = 'secret123';

    component.onSubmit();

    expect(mockAuthService.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'secret123',
    });
  });

  it('should request OTP code when the API requires it', () => {
    mockAuthService.login.mockReturnValue(
      of({ otp_required: true, username: 'testuser' }),
    );
    component.username = 'testuser';
    component.password = 'secret123';

    component.onSubmit();

    expect(component.otpRequired).toBe(true);
    expect(component.otpCode).toBe('');
    expect(component.loading).toBe(false);
  });

  it('renders a delayed OTP challenge without an extra user event in zoneless mode', async () => {
    const response = new Subject<{ otp_required: boolean; username: string }>();
    mockAuthService.login.mockReturnValue(response);
    component.username = 'testuser';
    component.password = 'secret123';
    fixture.nativeElement.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await fixture.whenStable();
    response.next({ otp_required: true, username: 'testuser' });
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('h1').textContent).toContain('Two-factor authentication');
  });

  it('should include OTP code after OTP is required', () => {
    component.username = 'testuser';
    component.password = 'secret123';
    component.otpRequired = true;
    component.otpCode = '123456';

    component.onSubmit();

    expect(mockAuthService.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'secret123',
      otp_code: '123456',
    });
  });

  it('submits a backup code unchanged through the recovery input', async () => {
    component.username = 'testuser';
    component.password = 'secret123';
    component.otpRequired = true;
    component.toggleBackupCode();
    fixture.detectChanges();
    await fixture.whenStable();
    const input = fixture.nativeElement.querySelector('#backup-code') as HTMLInputElement;
    input.value = 'a1b2c3d4';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    const form = fixture.nativeElement.querySelector('form');
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    expect(mockAuthService.login).toHaveBeenCalledWith({
      username: 'testuser', password: 'secret123', otp_code: 'a1b2c3d4',
    });
  });

  it('clears recovery codes when returning to the authenticator inputs', () => {
    component.toggleBackupCode();
    component.otpCode = 'a1b2c3d4';
    component.toggleBackupCode();
    expect(component.useBackupCode).toBe(false);
    expect(component.otpCode).toBe('');
  });

  it('should set loading to true when submitting', () => {
    // Return an observable that never completes so we can observe mid-flight state
    mockAuthService.login.mockReturnValue(new Observable(() => {}));
    component.username = 'user';
    component.password = 'pass';

    component.onSubmit();

    expect(component.loading).toBe(true);
  });

  it('should clear errorMessage on each submit attempt', () => {
    component.errorMessage = 'previous error';
    component.username = 'user';
    component.password = 'pass';

    component.onSubmit();

    // errorMessage is cleared at the start of onSubmit
    expect(component.errorMessage).toBe('');
  });

  it('should show error message on login failure with non_field_errors', () => {
    const errorResponse = {
      error: { non_field_errors: ['Unable to log in with provided credentials.'] },
    };
    mockAuthService.login.mockReturnValue(throwError(() => errorResponse));

    component.username = 'bad';
    component.password = 'wrong';
    component.onSubmit();

    expect(component.errorMessage).toBe(
      'Unable to log in with provided credentials.',
    );
    expect(component.loading).toBe(false);
  });

  it('should show error message on login failure with detail field', () => {
    const errorResponse = { error: { detail: 'Invalid credentials.' } };
    mockAuthService.login.mockReturnValue(throwError(() => errorResponse));

    component.username = 'bad';
    component.password = 'wrong';
    component.onSubmit();

    expect(component.errorMessage).toBe('Invalid credentials.');
  });

  it('should show OTP error messages', () => {
    const errorResponse = { error: { otp_code: ['Invalid OTP code.'] } };
    mockAuthService.login.mockReturnValue(throwError(() => errorResponse));

    component.username = 'bad';
    component.password = 'wrong';
    component.otpRequired = true;
    component.otpCode = '000000';
    component.onSubmit();

    expect(component.errorMessage).toBe('Invalid OTP code.');
  });

  it('should start with the password hidden', () => {
    expect(component.showPassword).toBe(false);
  });

  describe('backToCredentials', () => {
    beforeEach(() => {
      component.username = 'testuser';
      component.password = 'secret123';
      component.otpRequired = true;
      component.otpCode = '123456';
      component.errorMessage = 'Invalid OTP code.';
    });

    it('returns to the credentials step', () => {
      component.backToCredentials();
      expect(component.otpRequired).toBe(false);
    });

    it('clears the stale error', () => {
      component.backToCredentials();
      expect(component.errorMessage).toBe('');
    });

    it('clears the entered OTP so it cannot be resubmitted', () => {
      component.backToCredentials();
      expect(component.otpCode).toBe('');
    });

    it('clears the password rather than leaving it in memory', () => {
      component.backToCredentials();
      expect(component.password).toBe('');
    });

    it('keeps the username so it need not be retyped', () => {
      component.backToCredentials();
      expect(component.username).toBe('testuser');
    });
  });

  it('should show fallback error message when error has no known fields', () => {
    mockAuthService.login.mockReturnValue(throwError(() => ({ error: {} })));

    component.username = 'bad';
    component.password = 'wrong';
    component.onSubmit();

    expect(component.errorMessage).toBe(
      'Login failed. Please check your credentials.',
    );
  });
});
