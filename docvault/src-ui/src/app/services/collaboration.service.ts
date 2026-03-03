import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Comment,
  CheckoutStatus,
  CheckoutInfo,
  ShareLink,
  ShareLinkCreateRequest,
  PublicShareAccess,
  ActivityEntry,
} from '../models/collaboration.model';

@Injectable({ providedIn: 'root' })
export class CollaborationService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Comments
  getComments(documentId: number): Observable<Comment[]> {
    return this.http.get<Comment[]>(`${this.baseUrl}/documents/${documentId}/comments/`);
  }

  addComment(documentId: number, text: string): Observable<Comment> {
    return this.http.post<Comment>(`${this.baseUrl}/documents/${documentId}/comments/`, { text });
  }

  updateComment(documentId: number, commentId: number, text: string): Observable<Comment> {
    return this.http.patch<Comment>(`${this.baseUrl}/documents/${documentId}/comments/${commentId}/`, { text });
  }

  deleteComment(documentId: number, commentId: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/documents/${documentId}/comments/${commentId}/`);
  }

  // Check-in/Check-out
  getCheckoutStatus(documentId: number): Observable<CheckoutStatus> {
    return this.http.get<CheckoutStatus>(`${this.baseUrl}/documents/${documentId}/checkout_status/`);
  }

  checkout(documentId: number, expirationHours: number = 24): Observable<CheckoutInfo> {
    return this.http.post<CheckoutInfo>(`${this.baseUrl}/documents/${documentId}/checkout/`, { expiration_hours: expirationHours });
  }

  checkin(documentId: number): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(`${this.baseUrl}/documents/${documentId}/checkin/`, {});
  }

  // Share Links
  createShareLink(documentId: number, request: ShareLinkCreateRequest): Observable<ShareLink> {
    return this.http.post<ShareLink>(`${this.baseUrl}/documents/${documentId}/share/`, request);
  }

  getShareLinks(): Observable<ShareLink[]> {
    return this.http.get<ShareLink[]>(`${this.baseUrl}/share-links/`);
  }

  deleteShareLink(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/share-links/${id}/`);
  }

  accessShareLink(slug: string): Observable<PublicShareAccess> {
    return this.http.get<PublicShareAccess>(`${this.baseUrl}/share/${slug}/`);
  }

  verifySharePassword(slug: string, password: string): Observable<PublicShareAccess> {
    return this.http.post<PublicShareAccess>(`${this.baseUrl}/share/${slug}/`, { password });
  }

  // Activity
  getDocumentActivity(documentId: number): Observable<ActivityEntry[]> {
    return this.http.get<ActivityEntry[]>(`${this.baseUrl}/documents/${documentId}/activity/`);
  }

  getGlobalActivity(): Observable<ActivityEntry[]> {
    return this.http.get<ActivityEntry[]>(`${this.baseUrl}/activity/`);
  }
}
