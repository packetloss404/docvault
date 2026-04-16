import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from './auth.service';
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
  ChangePasswordRequest,
} from '../models/user.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        AuthService,
      ],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // --- Initial state ---

  it('isAuthenticated should be false when no token in localStorage', () => {
    expect(service.isAuthenticated()).toBe(false);
  });

  it('isAuthenticated should be true when a token exists in localStorage', () => {
    localStorage.setItem('docvault_token', 'stored-token');
    // Re-create service so signal reads the stored value
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        AuthService,
      ],
    });
    const svc = TestBed.inject(AuthService);
    expect(svc.isAuthenticated()).toBe(true);
    TestBed.inject(HttpTestingController).verify();
  });

  // --- login() ---

  describe('login()', () => {
    it('should POST credentials to /auth/login/', () => {
      const credentials: LoginRequest = { username: 'alice', password: 'secret' };
      const mockResponse: LoginResponse = {
        token: 'tok123',
        user_id: 1,
        username: 'alice',
        email: 'alice@example.com',
      };

      service.login(credentials).subscribe((res) => {
        expect(res).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${API}/auth/login/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(credentials);
      req.flush(mockResponse);
    });

    it('should store the token in localStorage after login', () => {
      const credentials: LoginRequest = { username: 'alice', password: 'secret' };
      const mockResponse: LoginResponse = {
        token: 'tok-stored',
        user_id: 1,
        username: 'alice',
        email: 'alice@example.com',
      };

      service.login(credentials).subscribe();
      httpMock.expectOne(`${API}/auth/login/`).flush(mockResponse);

      expect(localStorage.getItem('docvault_token')).toBe('tok-stored');
      expect(service.isAuthenticated()).toBe(true);
      expect(service.token()).toBe('tok-stored');
    });

    it('should propagate HTTP errors from login', () => {
      const credentials: LoginRequest = { username: 'bad', password: 'wrong' };
      let caughtError: unknown;

      service.login(credentials).subscribe({ error: (err) => (caughtError = err) });

      httpMock
        .expectOne(`${API}/auth/login/`)
        .flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });

      expect(caughtError).toBeTruthy();
    });
  });

  // --- register() ---

  describe('register()', () => {
    it('should POST data to /auth/register/', () => {
      const data: RegisterRequest = {
        username: 'bob',
        email: 'bob@example.com',
        password: 'pass',
      };
      const mockResponse: RegisterResponse = {
        token: 'reg-tok',
        user_id: 2,
        username: 'bob',
      };

      service.register(data).subscribe((res) => {
        expect(res).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${API}/auth/register/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush(mockResponse);
    });

    it('should store the token in localStorage after registration', () => {
      const data: RegisterRequest = {
        username: 'bob',
        email: 'bob@example.com',
        password: 'pass',
      };
      const mockResponse: RegisterResponse = { token: 'reg-tok', user_id: 2, username: 'bob' };

      service.register(data).subscribe();
      httpMock.expectOne(`${API}/auth/register/`).flush(mockResponse);

      expect(localStorage.getItem('docvault_token')).toBe('reg-tok');
      expect(service.isAuthenticated()).toBe(true);
    });
  });

  // --- logout() ---

  describe('logout()', () => {
    it('should POST to /auth/logout/', () => {
      service.logout().subscribe();

      const req = httpMock.expectOne(`${API}/auth/logout/`);
      expect(req.request.method).toBe('POST');
      req.flush(null);
    });

    it('should clear auth state and localStorage after logout', () => {
      // Set a token first
      localStorage.setItem('docvault_token', 'old-tok');
      service.login({ username: 'a', password: 'b' }).subscribe();
      httpMock
        .expectOne(`${API}/auth/login/`)
        .flush({ token: 'old-tok', user_id: 1, username: 'a', email: '' });

      service.logout().subscribe();
      httpMock.expectOne(`${API}/auth/logout/`).flush(null);

      expect(localStorage.getItem('docvault_token')).toBeNull();
      expect(service.isAuthenticated()).toBe(false);
    });
  });

  // --- getProfile() ---

  describe('getProfile()', () => {
    it('should GET /auth/profile/', () => {
      const mockUser: User = {
        id: 1,
        username: 'alice',
        email: 'alice@example.com',
        first_name: 'Alice',
        last_name: 'Smith',
        is_active: true,
        is_staff: false,
        date_joined: '2024-01-01',
      };

      service.getProfile().subscribe((user) => {
        expect(user).toEqual(mockUser);
      });

      const req = httpMock.expectOne(`${API}/auth/profile/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockUser);
    });

    it('should update the currentUser signal with the fetched profile', () => {
      const mockUser: User = {
        id: 1,
        username: 'alice',
        email: 'alice@example.com',
        first_name: 'Alice',
        last_name: 'Smith',
        is_active: true,
        is_staff: false,
        date_joined: '2024-01-01',
      };

      service.getProfile().subscribe();
      httpMock.expectOne(`${API}/auth/profile/`).flush(mockUser);

      expect(service.currentUser()).toEqual(mockUser);
    });

    it('should propagate HTTP errors from getProfile', () => {
      let caughtError: unknown;
      service.getProfile().subscribe({ error: (err) => (caughtError = err) });
      httpMock
        .expectOne(`${API}/auth/profile/`)
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(caughtError).toBeTruthy();
    });
  });

  // --- changePassword() ---

  describe('changePassword()', () => {
    it('should POST to /auth/change-password/', () => {
      const data: ChangePasswordRequest = {
        old_password: 'old',
        new_password: 'new',
      };
      const mockResponse = { token: 'new-tok' };

      service.changePassword(data).subscribe((res) => {
        expect(res).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${API}/auth/change-password/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush(mockResponse);
    });

    it('should update the stored token after a password change', () => {
      service
        .changePassword({ old_password: 'old', new_password: 'new' })
        .subscribe();

      httpMock
        .expectOne(`${API}/auth/change-password/`)
        .flush({ token: 'refreshed-tok' });

      expect(localStorage.getItem('docvault_token')).toBe('refreshed-tok');
      expect(service.token()).toBe('refreshed-tok');
    });
  });

  // --- clearAuth() ---

  describe('clearAuth()', () => {
    it('should clear token from localStorage and reset signals', () => {
      localStorage.setItem('docvault_token', 'tok');
      service.login({ username: 'a', password: 'b' }).subscribe();
      httpMock
        .expectOne(`${API}/auth/login/`)
        .flush({ token: 'tok', user_id: 1, username: 'a', email: '' });

      service.clearAuth();

      expect(localStorage.getItem('docvault_token')).toBeNull();
      expect(service.isAuthenticated()).toBe(false);
      expect(service.currentUser()).toBeNull();
    });
  });
});
