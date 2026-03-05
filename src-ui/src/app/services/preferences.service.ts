import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface UserPreferences {
  dashboard_layout?: string[];
  theme?: 'light' | 'dark' | 'system';
  [key: string]: unknown;
}

@Injectable({ providedIn: 'root' })
export class PreferencesService {
  private readonly apiUrl = `${environment.apiUrl}/preferences`;

  constructor(private http: HttpClient) {}

  getPreferences(): Observable<UserPreferences> {
    return this.http.get<UserPreferences>(`${this.apiUrl}/`);
  }

  updatePreferences(data: Partial<UserPreferences>): Observable<UserPreferences> {
    return this.http.patch<UserPreferences>(`${this.apiUrl}/`, data);
  }
}
