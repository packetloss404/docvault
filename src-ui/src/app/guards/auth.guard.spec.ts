import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('authGuard', () => {
  let authServiceMock: { isAuthenticated: ReturnType<typeof vi.fn> };
  let routerMock: { createUrlTree: ReturnType<typeof vi.fn> };
  let loginUrlTree: UrlTree;

  const runGuard = (): ReturnType<typeof authGuard> =>
    TestBed.runInInjectionContext(() => authGuard({} as any, {} as any));

  beforeEach(() => {
    loginUrlTree = {} as UrlTree;

    authServiceMock = {
      isAuthenticated: vi.fn(),
    };

    routerMock = {
      createUrlTree: vi.fn().mockReturnValue(loginUrlTree),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authServiceMock },
        { provide: Router, useValue: routerMock },
      ],
    });
  });

  it('returns true when the user is authenticated', () => {
    authServiceMock.isAuthenticated.mockReturnValue(true);

    const result = runGuard();

    expect(result).toBe(true);
  });

  it('redirects to /login when the user is not authenticated', () => {
    authServiceMock.isAuthenticated.mockReturnValue(false);

    const result = runGuard();

    expect(routerMock.createUrlTree).toHaveBeenCalledWith(['/login']);
    expect(result).toBe(loginUrlTree);
  });

  it('does not call createUrlTree when authenticated', () => {
    authServiceMock.isAuthenticated.mockReturnValue(true);

    runGuard();

    expect(routerMock.createUrlTree).not.toHaveBeenCalled();
  });
});
