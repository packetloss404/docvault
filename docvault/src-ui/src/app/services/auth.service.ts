import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
  ChangePasswordRequest,
} from '../models/user.model';

const TOKEN_KEY = 'docvault_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = environment.apiUrl;
  private tokenSignal = signal<string | null>(this.getStoredToken());
  private currentUserSignal = signal<User | null>(null);

  readonly isAuthenticated = computed(() => !!this.tokenSignal());
  readonly currentUser = computed(() => this.currentUserSignal());
  readonly token = computed(() => this.tokenSignal());

  constructor(
    private http: HttpClient,
    private router: Router,
  ) {}

  login(credentials: LoginRequest): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${this.apiUrl}/auth/login/`, credentials)
      .pipe(tap((res) => this.setToken(res.token)));
  }

  register(data: RegisterRequest): Observable<RegisterResponse> {
    return this.http
      .post<RegisterResponse>(`${this.apiUrl}/auth/register/`, data)
      .pipe(tap((res) => this.setToken(res.token)));
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/auth/logout/`, {}).pipe(
      tap(() => this.clearAuth()),
    );
  }

  getProfile(): Observable<User> {
    return this.http
      .get<User>(`${this.apiUrl}/auth/profile/`)
      .pipe(tap((user) => this.currentUserSignal.set(user)));
  }

  changePassword(data: ChangePasswordRequest): Observable<{ token: string }> {
    return this.http
      .post<{ token: string }>(`${this.apiUrl}/auth/change-password/`, data)
      .pipe(tap((res) => this.setToken(res.token)));
  }

  clearAuth(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.tokenSignal.set(null);
    this.currentUserSignal.set(null);
    this.router.navigate(['/login']);
  }

  private setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    this.tokenSignal.set(token);
  }

  private getStoredToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }
}
