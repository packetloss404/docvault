import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { SecurityService } from './security.service';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

describe('SecurityService', () => {
  let service: SecurityService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SecurityService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  // --- OTP ---

  describe('getOTPStatus', () => {
    it('sends GET to /auth/otp/status/', () => {
      service.getOTPStatus().subscribe();
      const req = httpTesting.expectOne(`${API}/auth/otp/status/`);
      expect(req.request.method).toBe('GET');
      req.flush({ enabled: false, confirmed: false });
    });
  });

  describe('setupOTP', () => {
    it('sends POST to /auth/otp/setup/ with empty body', () => {
      service.setupOTP().subscribe();
      const req = httpTesting.expectOne(`${API}/auth/otp/setup/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ secret: 'S3CR3T', provisioning_uri: 'otpauth://...', qr_code_base64: '' });
    });
  });

  describe('confirmOTP', () => {
    it('sends POST to /auth/otp/confirm/ with code', () => {
      service.confirmOTP('123456').subscribe();
      const req = httpTesting.expectOne(`${API}/auth/otp/confirm/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ code: '123456' });
      req.flush({ confirmed: true, backup_codes: [] });
    });
  });

  describe('disableOTP', () => {
    it('sends POST to /auth/otp/disable/ with password', () => {
      service.disableOTP('mypassword').subscribe();
      const req = httpTesting.expectOne(`${API}/auth/otp/disable/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ password: 'mypassword' });
      req.flush({ disabled: true });
    });
  });

  describe('verifyOTP', () => {
    it('sends POST to /auth/otp/verify/ with code', () => {
      service.verifyOTP('654321').subscribe();
      const req = httpTesting.expectOne(`${API}/auth/otp/verify/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ code: '654321' });
      req.flush({ verified: true, token: 'jwt-token' });
    });
  });

  // --- Signatures ---

  describe('signDocument', () => {
    it('sends POST to /documents/:id/sign/ with empty body when no keyId', () => {
      service.signDocument(42).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/sign/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ id: 1 });
    });

    it('sends POST with key_id in body when keyId provided', () => {
      service.signDocument(42, 'ABCD1234').subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/sign/`);
      expect(req.request.body).toEqual({ key_id: 'ABCD1234' });
      req.flush({ id: 1 });
    });
  });

  describe('getDocumentSignatures', () => {
    it('sends GET to /documents/:id/signatures/', () => {
      service.getDocumentSignatures(42).subscribe();
      const req = httpTesting.expectOne(`${API}/documents/42/signatures/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('verifyDocumentSignatures', () => {
    it('sends POST to /documents/:id/verify/ with empty body', () => {
      service.verifyDocumentSignatures(42).subscribe();
      const req = httpTesting.expectOne(
        `${API}/documents/42/verify/`,
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush({ results: [] });
    });
  });

  // --- GPG Keys ---

  describe('getGPGKeys', () => {
    it('sends GET to /gpg-keys/', () => {
      service.getGPGKeys().subscribe();
      const req = httpTesting.expectOne(`${API}/gpg-keys/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('importGPGKey', () => {
    it('sends POST to /gpg-keys/import/ with key_data', () => {
      const keyData = '-----BEGIN PGP PUBLIC KEY BLOCK-----\n...';
      service.importGPGKey(keyData).subscribe();
      const req = httpTesting.expectOne(`${API}/gpg-keys/import/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ key_data: keyData });
      req.flush({ key_id: 'ABCD1234', fingerprint: 'ABCD', uids: [], expires: '', length: '4096' });
    });
  });

  describe('deleteGPGKey', () => {
    it('sends DELETE to /gpg-keys/:keyId/', () => {
      service.deleteGPGKey('ABCD1234').subscribe();
      const req = httpTesting.expectOne(`${API}/gpg-keys/ABCD1234/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Audit Log ---

  describe('getAuditLog', () => {
    it('sends GET to /audit-log/ with no params by default', () => {
      service.getAuditLog().subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/audit-log/`,
      );
      expect(req.request.method).toBe('GET');
      req.flush({ results: [], count: 0 });
    });

    it('sends query params when provided', () => {
      service.getAuditLog({ page: 2, user: 5, action: 'create' }).subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/audit-log/`,
      );
      expect(req.request.params.get('page')).toBe('2');
      expect(req.request.params.get('user')).toBe('5');
      expect(req.request.params.get('action')).toBe('create');
      req.flush({ results: [], count: 0 });
    });

    it('omits params that are undefined or empty string', () => {
      service.getAuditLog({ page: 1, action: '', model_type: undefined }).subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/audit-log/`,
      );
      expect(req.request.params.get('page')).toBe('1');
      expect(req.request.params.has('action')).toBe(false);
      expect(req.request.params.has('model_type')).toBe(false);
      req.flush({ results: [], count: 0 });
    });
  });

  describe('exportAuditLog', () => {
    it('sends GET to /audit-log/export/ with format=csv', () => {
      service.exportAuditLog('csv').subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/audit-log/export/`,
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('format')).toBe('csv');
      req.flush(new Blob());
    });

    it('sends GET with format=json and additional params', () => {
      service.exportAuditLog('json', { user: 3 }).subscribe();
      const req = httpTesting.expectOne(
        (r) => r.url === `${API}/audit-log/export/`,
      );
      expect(req.request.params.get('format')).toBe('json');
      expect(req.request.params.get('user')).toBe('3');
      req.flush(new Blob());
    });
  });

  // --- Users ---

  describe('getUsers', () => {
    it('sends GET to /users/', () => {
      service.getUsers().subscribe();
      const req = httpTesting.expectOne(`${API}/users/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('getUser', () => {
    it('sends GET to /users/:id/', () => {
      service.getUser(3).subscribe();
      const req = httpTesting.expectOne(`${API}/users/3/`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 3 });
    });
  });

  describe('createUser', () => {
    it('sends POST to /users/ with payload', () => {
      const data = { username: 'jdoe', email: 'jdoe@example.com', password: 'secret' };
      service.createUser(data).subscribe();
      const req = httpTesting.expectOne(`${API}/users/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateUser', () => {
    it('sends PATCH to /users/:id/ with payload', () => {
      const data = { email: 'new@example.com' };
      service.updateUser(3, data).subscribe();
      const req = httpTesting.expectOne(`${API}/users/3/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 3, ...data });
    });
  });

  describe('deleteUser', () => {
    it('sends DELETE to /users/:id/', () => {
      service.deleteUser(3).subscribe();
      const req = httpTesting.expectOne(`${API}/users/3/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Groups ---

  describe('getGroups', () => {
    it('sends GET to /groups/', () => {
      service.getGroups().subscribe();
      const req = httpTesting.expectOne(`${API}/groups/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createGroup', () => {
    it('sends POST to /groups/ with payload', () => {
      const data = { name: 'Editors' };
      service.createGroup(data).subscribe();
      const req = httpTesting.expectOne(`${API}/groups/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateGroup', () => {
    it('sends PATCH to /groups/:id/ with payload', () => {
      const data = { name: 'Senior Editors' };
      service.updateGroup(1, data).subscribe();
      const req = httpTesting.expectOne(`${API}/groups/1/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('deleteGroup', () => {
    it('sends DELETE to /groups/:id/', () => {
      service.deleteGroup(1).subscribe();
      const req = httpTesting.expectOne(`${API}/groups/1/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Roles ---

  describe('getRoles', () => {
    it('sends GET to /roles/', () => {
      service.getRoles().subscribe();
      const req = httpTesting.expectOne(`${API}/roles/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('createRole', () => {
    it('sends POST to /roles/ with payload', () => {
      const data = { name: 'Admin', permission_ids: [1, 2, 3] };
      service.createRole(data).subscribe();
      const req = httpTesting.expectOne(`${API}/roles/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('updateRole', () => {
    it('sends PATCH to /roles/:id/ with payload', () => {
      const data = { name: 'Super Admin' };
      service.updateRole(1, data).subscribe();
      const req = httpTesting.expectOne(`${API}/roles/1/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });
  });

  describe('deleteRole', () => {
    it('sends DELETE to /roles/:id/', () => {
      service.deleteRole(1).subscribe();
      const req = httpTesting.expectOne(`${API}/roles/1/`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  // --- Permissions ---

  describe('getPermissions', () => {
    it('sends GET to /permissions/', () => {
      service.getPermissions().subscribe();
      const req = httpTesting.expectOne(`${API}/permissions/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  // --- Scanners ---

  describe('listScanners', () => {
    it('sends GET to /sources/scanners/', () => {
      service.listScanners().subscribe();
      const req = httpTesting.expectOne(`${API}/sources/scanners/`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('scan', () => {
    it('sends POST to /sources/scanners/:deviceId/scan/ with options', () => {
      const options = { dpi: 300, color_mode: 'color', paper_size: 'A4' };
      service.scan('scanner-01', options).subscribe();
      const req = httpTesting.expectOne(
        `${API}/sources/scanners/scanner-01/scan/`,
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(options);
      req.flush({ task_id: 'task-abc', message: 'Scanning started' });
    });

    it('sends POST with empty options by default', () => {
      service.scan('scanner-01').subscribe();
      const req = httpTesting.expectOne(
        `${API}/sources/scanners/scanner-01/scan/`,
      );
      expect(req.request.body).toEqual({});
      req.flush({ task_id: 'task-abc', message: 'Scanning started' });
    });
  });
});
