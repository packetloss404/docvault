import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PortalService } from './portal.service';
import { environment } from '../../environments/environment';

describe('PortalService API contracts', () => {
  let service: PortalService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PortalService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads full settings before rendering or editing lightweight portal summaries', () => {
    const portal = { id: 7, name: 'Contributor portal', require_name: true, require_email: true, max_file_size_mb: 25, primary_color: '#123456' };
    service.getPortals().subscribe((response) => expect(response.results).toEqual([portal]));
    http.expectOne(`${environment.apiUrl}/portals/`).flush({ count: 1, next: null, previous: null, results: [{ id: 7, name: portal.name }] });
    http.expectOne(`${environment.apiUrl}/portals/7/`).flush(portal);
  });

  it('normalizes the real bare submission queue without discarding document links', () => {
    const submission = { id: 9, status: 'pending_review', original_filename: 'contract.pdf', ingested_document: null };
    service.getSubmissions({ portal: 7 }).subscribe((response) => {
      expect(response.count).toBe(1);
      expect(response.results).toEqual([submission]);
    });
    const request = http.expectOne((request) => request.url === `${environment.apiUrl}/portal-submissions/`);
    expect(request.request.params.get('portal')).toBe('7');
    request.flush([submission]);
  });
});
