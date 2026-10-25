import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Subject, of } from 'rxjs';
import { DocumentSignaturesComponent } from './document-signatures.component';
import { SecurityService } from '../../services/security.service';
import { Signature } from '../../models/security.model';

const signature: Signature = {
  id: 1, document: 1, signer: 1, signer_username: 'signer', signature_data: '', key_id: 'test-key',
  algorithm: 'RSA', verified: true, verified_at: '2026-10-25T00:00:00Z', created_at: '2026-10-25T00:00:00Z',
};

describe('DocumentSignaturesComponent active file changes', () => {
  let fixture: ComponentFixture<DocumentSignaturesComponent>;
  let security: { getDocumentSignatures: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    security = { getDocumentSignatures: vi.fn(() => of([signature])) };
    TestBed.configureTestingModule({
      imports: [DocumentSignaturesComponent],
      providers: [{ provide: SecurityService, useValue: security }],
    });
    fixture = TestBed.createComponent(DocumentSignaturesComponent);
    fixture.componentRef.setInput('documentId', 1);
    fixture.componentRef.setInput('documentChecksum', 'version-one');
  });

  it('clears the previous verified badge while loading signatures for a new active checksum', () => {
    fixture.detectChanges();
    expect(fixture.componentInstance.signatures()[0].verified).toBe(true);
    const pending = new Subject<Signature[]>();
    security.getDocumentSignatures.mockReturnValue(pending);
    fixture.componentRef.setInput('documentChecksum', 'version-two');
    fixture.detectChanges();
    expect(fixture.componentInstance.signatures()).toEqual([]);
    expect(fixture.componentInstance.loading()).toBe(true);
    pending.next([{ ...signature, verified: false, verified_at: null }]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('unverified');
    expect(fixture.nativeElement.querySelector('.dv-chip--ok')).toBeNull();
  });

  it('cancels a stale signature request so an old verified result cannot overwrite the new file state', () => {
    const previous = new Subject<Signature[]>();
    const current = new Subject<Signature[]>();
    security.getDocumentSignatures.mockReturnValueOnce(previous).mockReturnValueOnce(current);
    fixture.detectChanges();
    fixture.componentRef.setInput('documentChecksum', 'version-two');
    fixture.detectChanges();
    expect(previous.observed).toBe(false);
    previous.next([signature]);
    current.next([{ ...signature, verified: false, verified_at: null }]);
    expect(fixture.componentInstance.signatures()[0].verified).toBe(false);
    fixture.destroy();
    expect(current.observed).toBe(false);
  });
});
