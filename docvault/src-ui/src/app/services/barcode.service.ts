import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { BarcodeConfig, BulkAsnResult } from '../models/barcode.model';

@Injectable({ providedIn: 'root' })
export class BarcodeService {
  private readonly barcodeUrl = `${environment.apiUrl}/barcode`;
  private readonly asnUrl = `${environment.apiUrl}/asn`;

  constructor(private http: HttpClient) {}

  getBarcodeConfig(): Observable<BarcodeConfig> {
    return this.http.get<BarcodeConfig>(`${this.barcodeUrl}/config/`);
  }

  getNextAsn(): Observable<{ next_asn: number }> {
    return this.http.get<{ next_asn: number }>(`${this.asnUrl}/next/`);
  }

  bulkAssignAsn(documentIds: number[]): Observable<BulkAsnResult> {
    return this.http.post<BulkAsnResult>(`${this.asnUrl}/bulk-assign/`, {
      document_ids: documentIds,
    });
  }
}
