import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { NotificationService } from './notification.service';
import { environment } from '../../environments/environment';

const BASE = environment.apiUrl;
const NOTIF_URL = `${BASE}/notifications`;
const PREF_URL = `${BASE}/notification-preferences`;
const QUOTA_URL = `${BASE}/quotas`;

describe('NotificationService', () => {
  let service: NotificationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        NotificationService,
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(NotificationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // --- Notifications ---

  describe('getNotifications', () => {
    it('should GET all notifications without filter', () => {
      const mockPage = { count: 1, results: [{ id: 1, title: 'Test' }] };

      service.getNotifications().subscribe((result) => {
        expect(result).toEqual(mockPage);
      });

      const req = httpMock.expectOne(`${NOTIF_URL}/`);
      expect(req.request.method).toBe('GET');
      expect(req.request.params.has('unread')).toBe(false);
      req.flush(mockPage);
    });

    it('should GET notifications with unread=true when flag is set', () => {
      const mockPage = { count: 1, results: [{ id: 2, title: 'Unread' }] };

      service.getNotifications(true).subscribe((result) => {
        expect(result).toEqual(mockPage);
      });

      const req = httpMock.expectOne(
        (r) => r.url === `${NOTIF_URL}/` && r.params.get('unread') === 'true',
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockPage);
    });
  });

  describe('markRead', () => {
    it('should POST to mark a notification read', () => {
      service.markRead(7).subscribe();

      const req = httpMock.expectOne(`${NOTIF_URL}/7/read/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(null);
    });
  });

  describe('markAllRead', () => {
    it('should POST to mark all notifications read', () => {
      service.markAllRead().subscribe();

      const req = httpMock.expectOne(`${NOTIF_URL}/read_all/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(null);
    });
  });

  describe('getUnreadCount', () => {
    it('should GET the unread notification count', () => {
      service.getUnreadCount().subscribe((result) => {
        expect(result).toEqual({ count: 5 });
      });

      const req = httpMock.expectOne(`${NOTIF_URL}/unread_count/`);
      expect(req.request.method).toBe('GET');
      req.flush({ count: 5 });
    });
  });

  // --- Notification Preferences ---

  describe('getPreferences', () => {
    it('should GET notification preferences', () => {
      const mockPage = { count: 1, results: [{ id: 1, event_type: 'upload' }] };

      service.getPreferences().subscribe((result) => {
        expect(result).toEqual(mockPage);
      });

      const req = httpMock.expectOne(`${PREF_URL}/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockPage);
    });
  });

  describe('createPreference', () => {
    it('should POST a new notification preference', () => {
      const data = { event_type: 'upload', channel: 'email' as const, enabled: true };
      const created = { id: 10, ...data, webhook_url: '' };

      service.createPreference(data).subscribe((result) => {
        expect(result).toEqual(created);
      });

      const req = httpMock.expectOne(`${PREF_URL}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush(created);
    });
  });

  describe('updatePreference', () => {
    it('should PATCH an existing notification preference', () => {
      const patch = { enabled: false };
      const updated = { id: 3, event_type: 'ocr', channel: 'in_app' as const, enabled: false, webhook_url: '' };

      service.updatePreference(3, patch).subscribe((result) => {
        expect(result).toEqual(updated);
      });

      const req = httpMock.expectOne(`${PREF_URL}/3/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(patch);
      req.flush(updated);
    });
  });

  describe('deletePreference', () => {
    it('should DELETE a notification preference', () => {
      service.deletePreference(4).subscribe();

      const req = httpMock.expectOne(`${PREF_URL}/4/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Quotas ---

  describe('getQuotaUsage', () => {
    it('should GET quota usage', () => {
      const mockUsage = {
        document_count: 50,
        storage_bytes: 1024,
        max_documents: 100,
        max_storage_bytes: 10240,
        documents_remaining: 50,
        storage_remaining: 9216,
      };

      service.getQuotaUsage().subscribe((result) => {
        expect(result).toEqual(mockUsage);
      });

      const req = httpMock.expectOne(`${QUOTA_URL}/usage/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockUsage);
    });
  });
});
