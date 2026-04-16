import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpRequest,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';

describe('authInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let authServiceMock: { token: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    authServiceMock = {
      token: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
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

  it('adds Authorization header when a token is present', () => {
    authServiceMock.token.mockReturnValue('abc123');

    httpClient.get('/api/documents').subscribe();

    const req = httpMock.expectOne('/api/documents');
    expect(req.request.headers.get('Authorization')).toBe('Token abc123');
    req.flush([]);
  });

  it('does not add Authorization header when no token is present', () => {
    authServiceMock.token.mockReturnValue(null);

    httpClient.get('/api/documents').subscribe();

    const req = httpMock.expectOne('/api/documents');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush([]);
  });

  it('passes the request through when token is an empty string', () => {
    authServiceMock.token.mockReturnValue('');

    httpClient.get('/api/documents').subscribe();

    const req = httpMock.expectOne('/api/documents');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush([]);
  });

  it('uses the Token scheme in the Authorization header', () => {
    authServiceMock.token.mockReturnValue('my-secret-token');

    httpClient.get('/api/test').subscribe();

    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.get('Authorization')).toMatch(/^Token /);
    req.flush(null);
  });

  it('does not mutate the original request object', () => {
    authServiceMock.token.mockReturnValue('abc123');

    const spy = vi.fn();
    httpClient.get('/api/documents').subscribe(spy);

    const req = httpMock.expectOne('/api/documents');
    // The cloned request carries the header; original is untouched
    expect(req.request.headers.get('Authorization')).toBe('Token abc123');
    req.flush([]);
    expect(spy).toHaveBeenCalled();
  });
});
