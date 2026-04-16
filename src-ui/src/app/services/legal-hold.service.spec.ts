import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { LegalHoldService } from './legal-hold.service';
import { environment } from '../../environments/environment';

const BASE = `${environment.apiUrl}/legal-holds`;

describe('LegalHoldService', () => {
  let service: LegalHoldService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(LegalHoldService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('getHolds', () => {
    it('sends GET to /legal-holds/ with no params by default', () => {
      service.getHolds().subscribe();
      const req = httpMock.expectOne(`${BASE}/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('sends GET with provided query params', () => {
      service.getHolds({ status: 'active' }).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/` && r.params.get('status') === 'active',
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('omits params with empty string values', () => {
      service.getHolds({ status: '', matter_number: 'ABC' }).subscribe();
      const req = httpMock.expectOne(
        (r) =>
          r.url === `${BASE}/` &&
          !r.params.has('status') &&
          r.params.get('matter_number') === 'ABC',
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getHold', () => {
    it('sends GET to /legal-holds/:id/', () => {
      service.getHold(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 1, name: 'Hold A', matter_number: 'M-001', description: '', status: 'draft', activated_at: null, released_at: null, release_reason: '', criteria_count: 0, custodian_count: 0, document_count: 0, created_at: '', updated_at: '' });
    });
  });

  describe('createHold', () => {
    it('sends POST to /legal-holds/ with body', () => {
      const data = { name: 'New Hold', matter_number: 'M-002' };
      service.createHold(data).subscribe();
      const req = httpMock.expectOne(`${BASE}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 2, ...data, description: '', status: 'draft', activated_at: null, released_at: null, release_reason: '', criteria_count: 0, custodian_count: 0, document_count: 0, created_at: '', updated_at: '' });
    });
  });

  describe('updateHold', () => {
    it('sends PATCH to /legal-holds/:id/ with body', () => {
      const data = { description: 'Updated description' };
      service.updateHold(1, data).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, name: 'Hold A', matter_number: 'M-001', description: 'Updated description', status: 'draft', activated_at: null, released_at: null, release_reason: '', criteria_count: 0, custodian_count: 0, document_count: 0, created_at: '', updated_at: '' });
    });
  });

  describe('activateHold', () => {
    it('sends POST to /legal-holds/:id/activate/ with empty body', () => {
      service.activateHold(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/activate/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ id: 1, status: 'active' });
    });
  });

  describe('releaseHold', () => {
    it('sends POST to /legal-holds/:id/release/ with reason in body', () => {
      service.releaseHold(1, 'Case closed').subscribe();
      const req = httpMock.expectOne(`${BASE}/1/release/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ reason: 'Case closed' });
      req.flush({ id: 1, status: 'released' });
    });
  });

  describe('getHoldDocuments', () => {
    it('sends GET to /legal-holds/:id/documents/', () => {
      service.getHoldDocuments(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/documents/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getHoldCustodians', () => {
    it('sends GET to /legal-holds/:id/custodians/', () => {
      service.getHoldCustodians(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/custodians/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('notifyCustodians', () => {
    it('sends POST to /legal-holds/:id/notify/ with empty body', () => {
      service.notifyCustodians(1).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/notify/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ notified: 3 });
    });
  });

  describe('acknowledgeCustodian', () => {
    it('sends POST to /legal-holds/:holdId/custodians/:custodianId/acknowledge/ with empty body', () => {
      service.acknowledgeCustodian(1, 7).subscribe();
      const req = httpMock.expectOne(`${BASE}/1/custodians/7/acknowledge/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ id: 7, user: 10, user_name: 'alice', notified_at: null, acknowledged: true, acknowledged_at: '2026-04-15', notes: '' });
    });
  });
});
