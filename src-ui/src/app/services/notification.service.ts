import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PaginatedResponse } from '../models/document.model';
import {
  Notification,
  NotificationPreference,
  QuotaUsage,
} from '../models/notification.model';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly notificationUrl = `${environment.apiUrl}/notifications`;
  private readonly preferenceUrl = `${environment.apiUrl}/notification-preferences`;
  private readonly quotaUrl = `${environment.apiUrl}/quotas`;

  constructor(private http: HttpClient) {}

  // --- Notifications ---

  getNotifications(unread?: boolean): Observable<PaginatedResponse<Notification>> {
    let params = new HttpParams();
    if (unread) {
      params = params.set('unread', 'true');
    }
    return this.http.get<PaginatedResponse<Notification>>(
      `${this.notificationUrl}/`,
      { params },
    );
  }

  markRead(id: number): Observable<void> {
    return this.http.post<void>(
      `${this.notificationUrl}/${id}/read/`,
      {},
    );
  }

  markAllRead(): Observable<void> {
    return this.http.post<void>(
      `${this.notificationUrl}/read_all/`,
      {},
    );
  }

  getUnreadCount(): Observable<{ count: number }> {
    return this.http.get<{ count: number }>(
      `${this.notificationUrl}/unread_count/`,
    );
  }

  // --- Notification Preferences ---

  getPreferences(): Observable<PaginatedResponse<NotificationPreference>> {
    return this.http.get<PaginatedResponse<NotificationPreference>>(
      `${this.preferenceUrl}/`,
    );
  }

  createPreference(
    data: Partial<NotificationPreference>,
  ): Observable<NotificationPreference> {
    return this.http.post<NotificationPreference>(
      `${this.preferenceUrl}/`,
      data,
    );
  }

  updatePreference(
    id: number,
    data: Partial<NotificationPreference>,
  ): Observable<NotificationPreference> {
    return this.http.patch<NotificationPreference>(
      `${this.preferenceUrl}/${id}/`,
      data,
    );
  }

  deletePreference(id: number): Observable<void> {
    return this.http.delete<void>(`${this.preferenceUrl}/${id}/`);
  }

  // --- Quotas ---

  getQuotaUsage(): Observable<QuotaUsage> {
    return this.http.get<QuotaUsage>(`${this.quotaUrl}/usage/`);
  }
}
