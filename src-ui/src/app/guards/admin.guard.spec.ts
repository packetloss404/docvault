import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { adminGuard } from './admin.guard';
import { AuthService } from '../services/auth.service';
import type { User } from '../models/user.model';

const makeUser = (overrides: Partial<User> = {}): User => ({
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_active: true,
  is_staff: false,
  date_joined: '2024-01-01T00:00:00Z',
  ...overrides,
});

describe('adminGuard', () => {
  let authServiceMock: {
    isAuthenticated: ReturnType<typeof vi.fn>;
    currentUser: ReturnType<typeof vi.fn>;
  };
  let routerMock: { createUrlTree: ReturnType<typeof vi.fn> };
  let loginUrlTree: UrlTree;
  let forbiddenUrlTree: UrlTree;

  const runGuard = (): ReturnType<typeof adminGuard> =>
    TestBed.runInInjectionContext(() => adminGuard({} as any, {} as any));

  beforeEach(() => {
    loginUrlTree = { login: true } as unknown as UrlTree;
    forbiddenUrlTree = { forbidden: true } as unknown as UrlTree;

    authServiceMock = {
      isAuthenticated: vi.fn(),
      currentUser: vi.fn(),
    };

    routerMock = {
      createUrlTree: vi.fn((path: string[]) => {
        return path[0] === '/login' ? loginUrlTree : forbiddenUrlTree;
      }),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authServiceMock },
        { provide: Router, useValue: routerMock },
      ],
    });
  });

  it('returns true when the user is authenticated and is staff', () => {
    authServiceMock.isAuthenticated.mockReturnValue(true);
    authServiceMock.currentUser.mockReturnValue(makeUser({ is_staff: true }));

    const result = runGuard();

    expect(result).toBe(true);
  });

  it('redirects to /403 when the user is authenticated but not staff', () => {
    authServiceMock.isAuthenticated.mockReturnValue(true);
    authServiceMock.currentUser.mockReturnValue(makeUser({ is_staff: false }));

    const result = runGuard();

    expect(routerMock.createUrlTree).toHaveBeenCalledWith(['/403']);
    expect(result).toBe(forbiddenUrlTree);
  });

  it('redirects to /login when the user is not authenticated', () => {
    authServiceMock.isAuthenticated.mockReturnValue(false);
    authServiceMock.currentUser.mockReturnValue(null);

    const result = runGuard();

    expect(routerMock.createUrlTree).toHaveBeenCalledWith(['/login']);
    expect(result).toBe(loginUrlTree);
  });

  it('redirects to /403 when current user is null but authenticated', () => {
    authServiceMock.isAuthenticated.mockReturnValue(true);
    authServiceMock.currentUser.mockReturnValue(null);

    const result = runGuard();

    expect(routerMock.createUrlTree).toHaveBeenCalledWith(['/403']);
    expect(result).toBe(forbiddenUrlTree);
  });
});
