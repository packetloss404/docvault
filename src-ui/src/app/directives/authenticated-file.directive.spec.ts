import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import {
  AuthenticatedDownloadDirective,
  AuthenticatedSrcDirective,
} from './authenticated-file.directive';
import { authInterceptor } from '../interceptors/auth.interceptor';
import { AuthService } from '../services/auth.service';

@Component({
  imports: [AuthenticatedSrcDirective, AuthenticatedDownloadDirective],
  template: `<img [authenticatedSrc]="source()" (error)="failed = true" />
    <iframe [authenticatedSrc]="frame()" (error)="failed = true"></iframe>
    <a href="#" authenticatedDownload="/api/v1/documents/1/download/">Download</a>`,
})
class HostComponent {
  source = signal('');
  frame = signal('');
  failed = false;
}

describe('authenticated file directives', () => {
  let http: HttpTestingController;
  const createObjectURL = vi.fn(() => 'blob:document');
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    vi.stubGlobal(
      'URL',
      class extends URL {
        static override createObjectURL = createObjectURL;
        static override revokeObjectURL = revokeObjectURL;
      },
    );
    createObjectURL.mockClear();
    revokeObjectURL.mockClear();
    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { token: () => 'private-token' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('authenticates previews and reuses the blob when only PDF page/zoom changes', () => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.frame.set('/api/v1/documents/1/download/#page=1');
    fixture.detectChanges();
    const request = http.expectOne('/api/v1/documents/1/download/');
    expect(request.request.headers.get('Authorization')).toBe('Token private-token');
    expect(request.request.responseType).toBe('blob');
    request.flush(new Blob(['pdf'], { type: 'application/pdf' }));
    const img = fixture.nativeElement.querySelector('iframe');
    expect(img.getAttribute('src')).toBe('blob:document#page=1');
    fixture.componentInstance.frame.set('/api/v1/documents/1/download/#page=2&zoom=150');
    fixture.detectChanges();
    http.expectNone('/api/v1/documents/1/download/');
    expect(img.getAttribute('src')).toBe('blob:document#page=2&zoom=150');
    fixture.destroy();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:document');
  });

  it('cancels stale previews and releases the previous blob when the document changes', () => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.source.set('/api/v1/documents/1/preview/');
    fixture.detectChanges();
    const stale = http.expectOne('/api/v1/documents/1/preview/');
    fixture.componentInstance.source.set('/api/v1/documents/2/preview/');
    fixture.detectChanges();
    expect(stale.cancelled).toBe(true);
    http.expectOne('/api/v1/documents/2/preview/').flush(new Blob(['image']));
    fixture.componentInstance.source.set('');
    fixture.detectChanges();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:document');
    expect(fixture.nativeElement.querySelector('img').hasAttribute('src')).toBe(false);
  });

  it('reports preview failures so thumbnail fallbacks can render', () => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.source.set('/api/v1/documents/1/preview/');
    fixture.detectChanges();
    http
      .expectOne('/api/v1/documents/1/preview/')
      .flush(new Blob(), { status: 404, statusText: 'Not Found' });
    expect(fixture.componentInstance.failed).toBe(true);
  });

  it('rejects active HTML content instead of embedding it in the application origin', () => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.frame.set('/api/v1/documents/1/download/');
    fixture.detectChanges();
    http.expectOne('/api/v1/documents/1/download/').flush(
      new Blob(['<script>alert(1)</script>'], { type: 'text/html' }),
    );
    expect(fixture.componentInstance.failed).toBe(true);
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('iframe').hasAttribute('src')).toBe(false);
  });

  it('downloads an authenticated blob with the server filename and releases it', () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    fixture.nativeElement
      .querySelector('a')
      .dispatchEvent(new MouseEvent('click', { cancelable: true }));
    const request = http.expectOne('/api/v1/documents/1/download/');
    expect(request.request.headers.get('Authorization')).toBe('Token private-token');
    request.flush(new Blob(['document']), {
      headers: { 'Content-Disposition': "attachment; filename*=UTF-8''r%C3%A9sum%C3%A9.pdf" },
    });
    expect(click).toHaveBeenCalledOnce();
    const link = click.mock.instances[0] as HTMLAnchorElement;
    expect(link.download).toBe('résumé.pdf');
    expect(link.href).toBe('blob:document');
    fixture.destroy();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:document');
  });
});
