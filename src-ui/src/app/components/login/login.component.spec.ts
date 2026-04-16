import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';

import { LoginComponent } from './login.component';
import { AuthService } from '../../services/auth.service';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let mockAuthService: { login: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockAuthService = {
      login: vi.fn().mockReturnValue(of({ token: 'fake-token' })),
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
