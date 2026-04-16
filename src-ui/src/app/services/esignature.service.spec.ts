import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { EsignatureService } from './esignature.service';
import { environment } from '../../environments/environment';

const BASE = environment.apiUrl;
const SIG_URL = `${BASE}/signature-requests`;
const SIGN_URL = `${BASE}/sign`;

const mockRequest = {
  id: 1,
  document: 10,
  title: 'Contract',
  message: 'Please sign',
  status: 'draft' as const,
  signing_order: 'sequential' as const,
  expiration: null,
  completed_at: null,
  signers: [],
  fields: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('EsignatureService', () => {
  let service: EsignatureService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        EsignatureService,
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(EsignatureService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // --- Authenticated endpoints ---

  describe('getRequests', () => {
    it('should GET all signature requests with no params', () => {
      service.getRequests().subscribe((result) => {
        expect(result).toEqual([mockRequest]);
      });

      const req = httpMock.expectOne(`${SIG_URL}/`);
      expect(req.request.method).toBe('GET');
      req.flush([mockRequest]);
    });

    it('should pass query params when provided', () => {
      service.getRequests({ status: 'sent', document: '10' }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${SIG_URL}/` &&
          r.params.get('status') === 'sent' &&
          r.params.get('document') === '10',
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('should omit empty string params', () => {
      service.getRequests({ status: '', document: '5' }).subscribe();

      const req = httpMock.expectOne(
        (r) => r.url === `${SIG_URL}/` && !r.params.has('status'),
      );
      expect(req.request.params.get('document')).toBe('5');
      req.flush([]);
    });
  });

  describe('getRequest', () => {
    it('should GET a single signature request', () => {
      service.getRequest(1).subscribe((result) => {
        expect(result).toEqual(mockRequest);
      });

      const req = httpMock.expectOne(`${SIG_URL}/1/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockRequest);
    });
  });

  describe('createRequest', () => {
    it('should POST to create a signature request on a document', () => {
      const data = { title: 'NDA', message: 'Please review' };

      service.createRequest(10, data).subscribe((result) => {
        expect(result).toEqual(mockRequest);
      });

      const req = httpMock.expectOne(
        `${BASE}/documents/10/signature-request/`,
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush(mockRequest);
    });
  });

  describe('sendRequest', () => {
    it('should POST to send a signature request', () => {
      const sent = { ...mockRequest, status: 'sent' as const };

      service.sendRequest(1).subscribe((result) => {
        expect(result).toEqual(sent);
      });

      const req = httpMock.expectOne(`${SIG_URL}/1/send/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(sent);
    });
  });

  describe('cancelRequest', () => {
    it('should POST to cancel a signature request', () => {
      const cancelled = { ...mockRequest, status: 'cancelled' as const };

      service.cancelRequest(1).subscribe((result) => {
        expect(result).toEqual(cancelled);
      });

      const req = httpMock.expectOne(`${SIG_URL}/1/cancel/`);
      expect(req.request.method).toBe('POST');
      req.flush(cancelled);
    });
  });

  describe('remindSigners', () => {
    it('should POST to send reminder to signers', () => {
      service.remindSigners(1).subscribe((result) => {
        expect(result).toEqual({ detail: 'Reminders sent.' });
      });

      const req = httpMock.expectOne(`${SIG_URL}/1/remind/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ detail: 'Reminders sent.' });
    });
  });

  describe('getAuditTrail', () => {
    it('should GET audit trail events for a request', () => {
      const events = [
        {
          id: 1,
          signer: null,
          event_type: 'created',
          detail: {},
          ip_address: null,
          timestamp: '2024-01-01T00:00:00Z',
        },
      ];

      service.getAuditTrail(1).subscribe((result) => {
        expect(result).toEqual(events);
      });

      const req = httpMock.expectOne(`${SIG_URL}/1/audit/`);
      expect(req.request.method).toBe('GET');
      req.flush(events);
    });
  });

  describe('downloadCertificate', () => {
    it('should GET the certificate as a Blob', () => {
      const blob = new Blob(['PDF content'], { type: 'application/pdf' });

      service.downloadCertificate(1).subscribe((result) => {
        expect(result).toBeInstanceOf(Blob);
      });

      const req = httpMock.expectOne(`${SIG_URL}/1/certificate/`);
      expect(req.request.method).toBe('GET');
      expect(req.request.responseType).toBe('blob');
      req.flush(blob);
    });
  });

  // --- Public signing endpoints ---

  describe('getSigningInfo', () => {
    it('should GET public signing info by token', () => {
      const info = {
        request_title: 'Contract',
        document_title: 'NDA',
        signer_name: 'Alice',
        signer_role: 'Signer',
        fields: [],
        page_count: 3,
        viewed_pages: [],
        status: 'sent',
      };

      service.getSigningInfo('tok123').subscribe((result) => {
        expect(result).toEqual(info);
      });

      const req = httpMock.expectOne(`${SIGN_URL}/tok123/`);
      expect(req.request.method).toBe('GET');
      req.flush(info);
    });
  });

  describe('recordPageView', () => {
    it('should POST a page view record', () => {
      service.recordPageView('tok123', 2).subscribe((result) => {
        expect(result).toEqual({ detail: 'ok' });
      });

      const req = httpMock.expectOne(`${SIGN_URL}/tok123/view_page/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ page: 2 });
      req.flush({ detail: 'ok' });
    });
  });

  describe('completeSigning', () => {
    it('should POST to complete signing with fields', () => {
      const fields = [{ id: 1, value: 'Alice' }];

      service.completeSigning('tok123', fields).subscribe((result) => {
        expect(result).toEqual({ detail: 'Signed.' });
      });

      const req = httpMock.expectOne(`${SIGN_URL}/tok123/complete/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ fields });
      req.flush({ detail: 'Signed.' });
    });
  });

  describe('declineSigning', () => {
    it('should POST to decline signing with a reason', () => {
      service.declineSigning('tok123', 'Not relevant').subscribe((result) => {
        expect(result).toEqual({ detail: 'Declined.' });
      });

      const req = httpMock.expectOne(`${SIGN_URL}/tok123/decline/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ reason: 'Not relevant' });
      req.flush({ detail: 'Declined.' });
    });
  });
});
