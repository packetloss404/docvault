import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  ChargeOut,
  DestructionCertificate,
  PhysicalLocation,
  PhysicalRecord,
} from '../models/physical-record.model';
import { PaginatedResponse } from '../models/document.model';

@Injectable({ providedIn: 'root' })
export class PhysicalRecordService {
  private readonly locationsUrl = `${environment.apiUrl}/physical-locations`;
  private readonly recordsUrl = `${environment.apiUrl}/physical-records`;
  private readonly chargeOutsUrl = `${environment.apiUrl}/charge-outs`;
  private readonly documentsUrl = `${environment.apiUrl}/documents`;

  constructor(private http: HttpClient) {}

  // --- Locations ---

  getLocations(
    params: Record<string, string> = {},
  ): Observable<PaginatedResponse<PhysicalLocation>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value);
      }
    }
    return this.http.get<PaginatedResponse<PhysicalLocation>>(
      `${this.locationsUrl}/`,
      { params: httpParams },
    );
  }

  getLocation(id: number): Observable<PhysicalLocation> {
    return this.http.get<PhysicalLocation>(`${this.locationsUrl}/${id}/`);
  }

  getLocationTree(): Observable<PhysicalLocation[]> {
    return this.http.get<PhysicalLocation[]>(`${this.locationsUrl}/tree/`);
  }

  createLocation(
    data: Partial<PhysicalLocation>,
  ): Observable<PhysicalLocation> {
    return this.http.post<PhysicalLocation>(`${this.locationsUrl}/`, data);
  }

  updateLocation(
    id: number,
    data: Partial<PhysicalLocation>,
  ): Observable<PhysicalLocation> {
    return this.http.patch<PhysicalLocation>(
      `${this.locationsUrl}/${id}/`,
      data,
    );
  }

  deleteLocation(id: number): Observable<void> {
    return this.http.delete<void>(`${this.locationsUrl}/${id}/`);
  }

  // --- Physical Records ---

  getRecords(
    params: Record<string, string> = {},
  ): Observable<PaginatedResponse<PhysicalRecord>> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value);
      }
    }
    return this.http.get<PaginatedResponse<PhysicalRecord>>(
      `${this.recordsUrl}/`,
      { params: httpParams },
    );
  }

  getRecord(id: number): Observable<PhysicalRecord> {
    return this.http.get<PhysicalRecord>(`${this.recordsUrl}/${id}/`);
  }

  createRecord(data: Partial<PhysicalRecord>): Observable<PhysicalRecord> {
    return this.http.post<PhysicalRecord>(`${this.recordsUrl}/`, data);
  }

  updateRecord(
    id: number,
    data: Partial<PhysicalRecord>,
  ): Observable<PhysicalRecord> {
    return this.http.patch<PhysicalRecord>(
      `${this.recordsUrl}/${id}/`,
      data,
    );
  }

  deleteRecord(id: number): Observable<void> {
    return this.http.delete<void>(`${this.recordsUrl}/${id}/`);
  }

  // --- Charge Out / In ---

  chargeOut(
    documentId: number,
    data: { expected_return: string; notes?: string },
  ): Observable<ChargeOut> {
    return this.http.post<ChargeOut>(
      `${this.documentsUrl}/${documentId}/charge-out/`,
      data,
    );
  }

  chargeIn(
    documentId: number,
    data: { notes?: string },
  ): Observable<ChargeOut> {
    return this.http.post<ChargeOut>(
      `${this.documentsUrl}/${documentId}/charge-in/`,
      data,
    );
  }

  getChargeOuts(
    params: Record<string, string> = {},
  ): Observable<ChargeOut[]> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value);
      }
    }
    return this.http.get<ChargeOut[]>(`${this.chargeOutsUrl}/`, {
      params: httpParams,
    });
  }

  getOverdueChargeOuts(): Observable<ChargeOut[]> {
    return this.http.get<ChargeOut[]>(`${this.chargeOutsUrl}/overdue/`);
  }

  // --- Destruction Certificates ---

  generateDestructionCertificate(
    recordId: number,
    data: { method: string; witness?: string; notes?: string },
  ): Observable<DestructionCertificate> {
    return this.http.post<DestructionCertificate>(
      `${this.recordsUrl}/${recordId}/destruction-certificate/`,
      data,
    );
  }
}
