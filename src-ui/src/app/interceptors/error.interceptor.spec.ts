import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { errorInterceptor } from './error.interceptor';
import { AuthService } from '../services/auth.service';

describe('errorInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let authServiceMock: { clearAuth: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    authServiceMock = {
      clearAuth: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceMock },
      ],
    });

    httpClient = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('calls clearAuth on a 401 response from a non-login URL', () => {
    httpClient.get('/api/documents').subscribe({ error: () => {} });

    const req = httpMock.expectOne('/api/documents');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

    expect(authServiceMock.clearAuth).toHaveBeenCalledTimes(1);
  });

  it('does not call clearAuth on a 401 response from the login URL', () => {
    httpClient.post('/auth/login', {}).subscribe({ error: () => {} });

    const req = httpMock.expectOne('/auth/login');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

    expect(authServiceMock.clearAuth).not.toHaveBeenCalled();
  });

  it('re-throws the error after handling a 401', () => {
    let caughtError: any;
    httpClient.get('/api/documents').subscribe({
      error: (err) => {
        caughtError = err;
      },
    });

    const req = httpMock.expectOne('/api/documents');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

    expect(caughtError).toBeDefined();
    expect(caughtError.status).toBe(401);
  });

  it('does not call clearAuth on a 403 response', () => {
    httpClient.get('/api/documents').subscribe({ error: () => {} });

    const req = httpMock.expectOne('/api/documents');
    req.flush('Forbidden', { status: 403, statusText: 'Forbidden' });

    expect(authServiceMock.clearAuth).not.toHaveBeenCalled();
  });

  it('re-throws the error on a 403 response', () => {
    let caughtError: any;
    httpClient.get('/api/documents').subscribe({
      error: (err) => {
        caughtError = err;
      },
    });

    const req = httpMock.expectOne('/api/documents');
    req.flush('Forbidden', { status: 403, statusText: 'Forbidden' });

    expect(caughtError.status).toBe(403);
  });

  it('does not call clearAuth on a 500 response', () => {
    httpClient.get('/api/documents').subscribe({ error: () => {} });

    const req = httpMock.expectOne('/api/documents');
    req.flush('Server Error', {
      status: 500,
      statusText: 'Internal Server Error',
    });

    expect(authServiceMock.clearAuth).not.toHaveBeenCalled();
  });

  it('re-throws the error on a 500 response', () => {
    let caughtError: any;
    httpClient.get('/api/documents').subscribe({
      error: (err) => {
        caughtError = err;
      },
    });

    const req = httpMock.expectOne('/api/documents');
    req.flush('Server Error', {
      status: 500,
      statusText: 'Internal Server Error',
    });

    expect(caughtError.status).toBe(500);
  });

  it('passes through successful responses without calling clearAuth', () => {
    httpClient.get('/api/documents').subscribe();

    const req = httpMock.expectOne('/api/documents');
    req.flush([{ id: 1 }]);

    expect(authServiceMock.clearAuth).not.toHaveBeenCalled();
  });
});
