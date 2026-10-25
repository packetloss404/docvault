import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { EsignatureService } from '../../services/esignature.service';
import { AuthenticatedSrcDirective } from '../../directives/authenticated-file.directive';
import {
  PublicSigningInfo,
  SignatureField,
} from '../../models/esignature.model';

@Component({
  selector: 'app-public-signing',
  standalone: true,
  imports: [CommonModule, FormsModule, AuthenticatedSrcDirective],
  template: `
    <div class="dv-auth">
      <div class="dv-auth__col psg__col" [class.psg__col--narrow]="!info()">
        <div class="dv-auth__brand">
          <div class="dv-auth__logo">V</div>
          <div>
            <div class="dv-auth__name">DocVault</div>
            <div class="dv-meta">signing</div>
          </div>
        </div>

        @if (loading()) {
          <div class="dv-auth__card psg__state">
            <span class="dv-spinner"></span>
            <span class="dv-meta">loading signing request…</span>
          </div>
        } @else if (errorMsg()) {
          <div class="dv-auth__card" role="alert">
            <span class="dv-chip dv-chip--upper dv-chip--warn psg__badge">unavailable</span>
            <div class="psg__msg">{{ errorMsg() }}</div>
          </div>
        } @else if (completed()) {
          <div class="dv-auth__card" role="status">
            <span class="dv-chip dv-chip--upper dv-chip--ok psg__badge">done</span>
            <div class="dv-h2">{{ completedMessage() }}</div>
          </div>
        } @else if (info()) {
          <div class="dv-auth__card psg__brief">
            <h1 class="dv-h2">{{ info()!.request_title }}</h1>
            <div class="dv-kv psg__kv">
              <span class="dv-kv__k">document</span>
              <span>{{ info()!.document_title }}</span>
              <span class="dv-kv__k">signing as</span>
              <span>
                <strong>{{ info()!.signer_name }}</strong>
                @if (info()!.signer_role) {
                  <span class="dv-meta psg__role">{{ info()!.signer_role }}</span>
                }
              </span>
            </div>
          </div>

          @if (info()!.status === 'signed') {
            <div class="dv-callout psg__note" role="status">
              <div class="dv-callout__label">already signed</div>
              <div class="psg__msg">You have already signed this document.</div>
            </div>
          } @else if (info()!.status === 'declined') {
            <div class="dv-auth__card psg__declined" role="status">
              <span class="dv-chip dv-chip--upper dv-chip--danger psg__badge">declined</span>
              <div class="psg__msg">You have declined this signing request.</div>
            </div>
          } @else {
            <div class="psg__split">
              <!-- Document pages -->
              <div class="dv-auth__card psg__pages">
                <span class="dv-eyebrow">pages reviewed</span>
                <div class="psg__pagegrid">
                  @for (pageNum of pageNumbers(); track pageNum) {
                    <button
                      type="button"
                      class="psg__page"
                      [class.is-viewed]="isPageViewed(pageNum)"
                      [attr.aria-pressed]="isPageViewed(pageNum)"
                      [title]="
                        isPageViewed(pageNum)
                          ? 'View reviewed page ' + pageNum
                          : 'View page ' + pageNum
                      "
                      (click)="currentPage.set(pageNum)"
                    >
                      @if (isPageViewed(pageNum)) {
                        <span aria-hidden="true">✓</span>
                      }
                      p.{{ pageNum }}
                    </button>
                  }
                </div>
                <img
                  class="psg__document"
                  style="width:100%;height:auto"
                  [authenticatedSrc]="previewUrl()"
                  [alt]="'Signing document, page ' + currentPage()"
                  (load)="viewPage(currentPage())"
                  (error)="previewError.set('Could not display the document. Please contact the sender before signing.')"
                />
                @if (previewError()) {
                  <div class="psg__error" role="alert">{{ previewError() }}</div>
                }
                <span class="dv-meta"
                  >{{ viewedPages().length }} of {{ pageNumbers().length }}
                  marked</span
                >
              </div>

              <!-- Signature fields -->
              <div class="dv-auth__card psg__fields">
                <span class="dv-eyebrow">signature fields</span>

                @for (field of info()!.fields; track field.id) {
                  <div class="psg__field">
                    <span class="dv-field__label">
                      {{ formatFieldType(field.field_type) }}
                      @if (field.required) {
                        <span class="dv-danger">*</span>
                      }
                      <span class="psg__page-ref">p.{{ field.page }}</span>
                    </span>

                    @if (field.field_type === 'checkbox') {
                      <button
                        type="button"
                        class="psg__check"
                        (click)="
                          setFieldValue(
                            field.id,
                            fieldValues()[field.id] === 'true' ? 'false' : 'true'
                          )
                        "
                        [attr.aria-pressed]="fieldValues()[field.id] === 'true'"
                      >
                        <span
                          class="dv-check"
                          [class.is-checked]="fieldValues()[field.id] === 'true'"
                          aria-hidden="true"
                        >
                          @if (fieldValues()[field.id] === 'true') {
                            ✓
                          }
                        </span>
                        <span class="psg__checklabel">I agree</span>
                      </button>
                    } @else if (
                      field.field_type === 'signature' ||
                      field.field_type === 'initials'
                    ) {
                      <button
                        type="button"
                        class="dv-dropzone psg__sign"
                        (click)="
                          setFieldValue(
                            field.id,
                            field.field_type === 'signature'
                              ? info()!.signer_name
                              : getInitials()
                          )
                        "
                      >
                        @if (fieldValues()[field.id]) {
                          <span class="psg__signature">{{
                            fieldValues()[field.id]
                          }}</span>
                        } @else {
                          <span
                            >Click to
                            {{
                              field.field_type === 'signature'
                                ? 'sign'
                                : 'initial'
                            }}</span
                          >
                        }
                      </button>
                    } @else {
                      <input
                        type="text"
                        class="dv-input"
                        [ngModel]="fieldValues()[field.id] || ''"
                        (ngModelChange)="setFieldValue(field.id, $event)"
                        [placeholder]="formatFieldType(field.field_type)"
                      />
                    }
                  </div>
                }

                @if (submitError()) {
                  <div class="psg__error" role="alert">{{ submitError() }}</div>
                }

                <div class="psg__actions">
                  <button
                    type="button"
                    class="dv-btn dv-btn--primary psg__sub"
                    (click)="completeSign()"
                    [disabled]="submitting()"
                  >
                    @if (submitting()) {
                      <span class="dv-spinner"></span>
                      Signing…
                    } @else {
                      Sign & complete →
                    }
                  </button>
                  <button
                    type="button"
                    class="dv-btn dv-btn--danger"
                    (click)="showDecline.set(true)"
                    [disabled]="submitting()"
                  >
                    Decline
                  </button>
                </div>

                @if (showDecline()) {
                  <div class="psg__decline">
                    <span class="dv-field__label" id="psg-decline-label"
                      >reason for declining</span
                    >
                    <textarea
                      class="dv-input psg__reason"
                      rows="3"
                      aria-labelledby="psg-decline-label"
                      placeholder="Please provide a reason…"
                      [ngModel]="declineReason()"
                      (ngModelChange)="declineReason.set($event)"
                    ></textarea>
                    <div class="psg__actions">
                      <button
                        type="button"
                        class="dv-btn dv-btn--danger"
                        (click)="decline()"
                        [disabled]="submitting()"
                      >
                        Confirm decline
                      </button>
                      <button
                        type="button"
                        class="dv-btn dv-btn--ghost"
                        (click)="showDecline.set(false)"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        }
      </div>
    </div>
  `,
  styleUrl: './public-signing.component.scss',
})
export class PublicSigningComponent implements OnInit {
  currentPage = signal(1);
  previewError = signal('');
  info = signal<PublicSigningInfo | null>(null);
  loading = signal(true);
  errorMsg = signal('');
  completed = signal(false);
  completedMessage = signal('');

  fieldValues = signal<Record<number, string>>({});
  viewedPages = signal<number[]>([]);

  submitting = signal(false);
  submitError = signal('');
  showDecline = signal(false);
  declineReason = signal('');

  private token = '';

  constructor(
    private route: ActivatedRoute,
    private esignatureService: EsignatureService,
  ) {}

  ngOnInit(): void {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    this.loadSigningInfo();
  }

  loadSigningInfo(): void {
    this.loading.set(true);
    this.esignatureService.getSigningInfo(this.token).subscribe({
      next: (data) => {
        this.info.set(data);
        this.viewedPages.set([...data.viewed_pages]);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMsg.set(
          err.status === 404
            ? 'Signing link not found or expired.'
            : 'Unable to load signing information.',
        );
        this.loading.set(false);
      },
    });
  }

  pageNumbers(): number[] {
    const count = this.info()?.page_count || 0;
    return Array.from({ length: count }, (_, i) => i + 1);
  }

  previewUrl(): string {
    return this.esignatureService.getSigningPreviewUrl(this.token, this.currentPage());
  }

  isPageViewed(page: number): boolean {
    return this.viewedPages().includes(page);
  }

  viewPage(page: number): void {
    if (this.isPageViewed(page)) return;
    this.esignatureService.recordPageView(this.token, page).subscribe({
      next: () => {
        this.viewedPages.update((pages) => [...pages, page]);
      },
    });
  }

  setFieldValue(fieldId: number, value: string): void {
    this.fieldValues.update((vals) => ({ ...vals, [fieldId]: value }));
  }

  getInitials(): string {
    const name = this.info()?.signer_name || '';
    return name
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase())
      .join('');
  }

  formatFieldType(type: string): string {
    return type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  completeSign(): void {
    const infoVal = this.info();
    if (!infoVal) return;
    if (this.previewError() || this.viewedPages().length < this.pageNumbers().length) {
      this.submitError.set('Review every document page before signing.');
      return;
    }

    // Validate required fields
    const vals = this.fieldValues();
    const missing = infoVal.fields.filter(
      (f) => f.required && !vals[f.id],
    );
    if (missing.length > 0) {
      this.submitError.set('Please complete all required fields before signing.');
      return;
    }

    this.submitting.set(true);
    this.submitError.set('');

    const fieldData = infoVal.fields.map((f) => ({
      id: f.id,
      value: vals[f.id] || '',
    }));

    this.esignatureService.completeSigning(this.token, fieldData).subscribe({
      next: () => {
        this.submitting.set(false);
        this.completed.set(true);
        this.completedMessage.set(
          'Thank you! Your signature has been recorded.',
        );
      },
      error: (err) => {
        this.submitting.set(false);
        this.submitError.set(
          err.error?.detail || 'Signing failed. Please try again.',
        );
      },
    });
  }

  decline(): void {
    this.submitting.set(true);
    this.submitError.set('');

    this.esignatureService
      .declineSigning(this.token, this.declineReason())
      .subscribe({
        next: () => {
          this.submitting.set(false);
          this.completed.set(true);
          this.completedMessage.set('You have declined this signing request.');
        },
        error: (err) => {
          this.submitting.set(false);
          this.submitError.set(
            err.error?.detail || 'Failed to decline. Please try again.',
          );
        },
      });
  }
}
