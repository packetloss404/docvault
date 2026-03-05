import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  LegalHold,
  LegalHoldCustodian,
  LegalHoldDocument,
} from '../models/legal-hold.model';

@Injectable({ providedIn: 'root' })
export class LegalHoldService {
  private readonly apiUrl = `${environment.apiUrl}/legal-holds`;

  constructor(private http: HttpClient) {}

  getHolds(
    params: Record<string, string> = {},
  ): Observable<LegalHold[]> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value);
      }
    }
    return this.http.get<LegalHold[]>(`${this.apiUrl}/`, {
      params: httpParams,
    });
  }

  getHold(id: number): Observable<LegalHold> {
    return this.http.get<LegalHold>(`${this.apiUrl}/${id}/`);
  }

  createHold(data: Partial<LegalHold>): Observable<LegalHold> {
    return this.http.post<LegalHold>(`${this.apiUrl}/`, data);
  }

  updateHold(id: number, data: Partial<LegalHold>): Observable<LegalHold> {
    return this.http.patch<LegalHold>(`${this.apiUrl}/${id}/`, data);
  }

  activateHold(id: number): Observable<LegalHold> {
    return this.http.post<LegalHold>(
      `${this.apiUrl}/${id}/activate/`,
      {},
    );
  }

  releaseHold(
    id: number,
    reason: string,
  ): Observable<LegalHold> {
    return this.http.post<LegalHold>(
      `${this.apiUrl}/${id}/release/`,
      { reason },
    );
  }

  getHoldDocuments(id: number): Observable<LegalHoldDocument[]> {
    return this.http.get<LegalHoldDocument[]>(
      `${this.apiUrl}/${id}/documents/`,
    );
  }

  getHoldCustodians(id: number): Observable<LegalHoldCustodian[]> {
    return this.http.get<LegalHoldCustodian[]>(
      `${this.apiUrl}/${id}/custodians/`,
    );
  }

  notifyCustodians(id: number): Observable<{ notified: number }> {
    return this.http.post<{ notified: number }>(
      `${this.apiUrl}/${id}/notify/`,
      {},
    );
  }

  acknowledgeCustodian(
    holdId: number,
    custodianId: number,
  ): Observable<LegalHoldCustodian> {
    return this.http.post<LegalHoldCustodian>(
      `${this.apiUrl}/${holdId}/custodians/${custodianId}/acknowledge/`,
      {},
    );
  }
}
