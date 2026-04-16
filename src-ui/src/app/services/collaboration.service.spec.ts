import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { CollaborationService } from './collaboration.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

describe('CollaborationService', () => {
  let service: CollaborationService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(CollaborationService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  // --- Comments ---

  describe('getComments', () => {
    it('sends GET to /documents/:id/comments/', () => {
      service.getComments(42).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/comments/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('addComment', () => {
    it('sends POST to /documents/:id/comments/ with text payload', () => {
      service.addComment(42, 'Great document!').subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/comments/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ text: 'Great document!' });
      req.flush({ id: 1, text: 'Great document!' });
    });
  });

  describe('updateComment', () => {
    it('sends PATCH to /documents/:id/comments/:commentId/ with text payload', () => {
      service.updateComment(42, 7, 'Edited text').subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/comments/7/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ text: 'Edited text' });
      req.flush({ id: 7, text: 'Edited text' });
    });
  });

  describe('deleteComment', () => {
    it('sends DELETE to /documents/:id/comments/:commentId/', () => {
      service.deleteComment(42, 7).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/comments/7/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Check-in / Check-out ---

  describe('getCheckoutStatus', () => {
    it('sends GET to /documents/:id/checkout_status/', () => {
      service.getCheckoutStatus(42).subscribe();
      const req = httpTesting.expectOne(
        `${API}/documents/42/checkout_status/`,
      );
      expect(req.request.method).toBe('GET');
      req.flush({ checked_out: false });
    });
  });

  describe('checkout', () => {
    it('sends POST to /documents/:id/checkout/ with default expiration', () => {
      service.checkout(42).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/checkout/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ expiration_hours: 24 });
      req.flush({ id: 1 });
    });

    it('sends POST with custom expiration_hours', () => {
      service.checkout(42, 48).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/checkout/`);
      expect(req.request.body).toEqual({ expiration_hours: 48 });
      req.flush({ id: 1 });
    });
  });

  describe('checkin', () => {
    it('sends POST to /documents/:id/checkin/ with empty body', () => {
      service.checkin(42).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/checkin/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ status: 'checked_in' });
    });
  });

  // --- Share Links ---

  describe('createShareLink', () => {
    it('sends POST to /documents/:id/share/ with request payload', () => {
      const shareReq = { expires_in_hours: 72, password: 'secret' };
      service.createShareLink(42, shareReq).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/share/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(shareReq);
      req.flush({ id: 10, slug: 'abc123' });
    });
  });

  describe('getShareLinks', () => {
    it('sends GET to /share-links/', () => {
      service.getShareLinks().subscribe();
      const req = httpTesting.expectOne(`${API}/share-links/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('deleteShareLink', () => {
    it('sends DELETE to /share-links/:id/', () => {
      service.deleteShareLink(10).subscribe();
      const req = httpTesting.expectOne(`${API}/share-links/10/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('accessShareLink', () => {
    it('sends GET to /share/:slug/', () => {
      service.accessShareLink('abc123').subscribe();
      const req = httpTesting.expectOne(`${API}/share/abc123/`);
      expect(req.request.method).toBe('GET');
      req.flush({ document: { id: 42 } });
    });
  });

  describe('verifySharePassword', () => {
    it('sends POST to /share/:slug/ with password payload', () => {
      service.verifySharePassword('abc123', 'secret').subscribe();
      const req = httpTesting.expectOne(`${API}/share/abc123/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ password: 'secret' });
      req.flush({ document: { id: 42 } });
    });
  });

  // --- Activity ---

  describe('getDocumentActivity', () => {
    it('sends GET to /documents/:id/activity/', () => {
      service.getDocumentActivity(42).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/activity/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getGlobalActivity', () => {
    it('sends GET to /activity/', () => {
      service.getGlobalActivity().subscribe();
      const req = httpTesting.expectOne(`${API}/activity/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });
});
