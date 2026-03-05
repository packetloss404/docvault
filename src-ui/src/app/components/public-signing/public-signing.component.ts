import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { EsignatureService } from '../../services/esignature.service';
import {
  PublicSigningInfo,
  SignatureField,
} from '../../models/esignature.model';

@Component({
  selector: 'app-public-signing',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (loading()) {
      <div class="d-flex justify-content-center align-items-center" style="min-height: 100vh;">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (errorMsg()) {
      <div class="d-flex justify-content-center align-items-center" style="min-height: 100vh;">
        <div class="text-center">
          <i class="bi bi-exclamation-triangle fs-1 text-warning"></i>
          <p class="mt-2">{{ errorMsg() }}</p>
        </div>
      </div>
    } @else if (completed()) {
      <div class="d-flex justify-content-center align-items-center" style="min-height: 100vh;">
        <div class="text-center">
          <i class="bi bi-check-circle fs-1 text-success"></i>
          <h4 class="mt-3">{{ completedMessage() }}</h4>
        </div>
      </div>
    } @else if (info()) {
      <div style="min-height: 100vh; background: #f8f9fa;">
        <!-- Header -->
        <nav class="navbar navbar-dark bg-primary px-3">
          <span class="navbar-brand mb-0 h1">DocVault Signing</span>
        </nav>

        <div class="container py-4" style="max-width: 900px;">
          <!-- Request Info -->
          <div class="card mb-4">
            <div class="card-body">
              <h5>{{ info()!.request_title }}</h5>
              <p class="text-muted mb-1">Document: {{ info()!.document_title }}</p>
              <p class="mb-0">
                Signing as: <strong>{{ info()!.signer_name }}</strong>
                @if (info()!.signer_role) {
                  <span class="text-muted">({{ info()!.signer_role }})</span>
                }
              </p>
            </div>
          </div>

          @if (info()!.status === 'signed') {
            <div class="alert alert-success">
              <i class="bi bi-check-circle me-1"></i>
              You have already signed this document.
            </div>
          } @else if (info()!.status === 'declined') {
            <div class="alert alert-danger">
              <i class="bi bi-x-circle me-1"></i>
              You have declined this signing request.
            </div>
          } @else {
            <!-- Page Viewer -->
            <div class="card mb-4">
              <div class="card-header">
                <i class="bi bi-file-earmark-text me-1"></i>Document Pages
              </div>
              <div class="card-body">
                <div class="row g-2">
                  @for (pageNum of pageNumbers(); track pageNum) {
                    <div class="col-auto">
                      <button
                        class="btn btn-sm"
                        [ngClass]="{
                          'btn-success': isPageViewed(pageNum),
                          'btn-outline-secondary': !isPageViewed(pageNum)
                        }"
                        (click)="viewPage(pageNum)"
                      >
                        @if (isPageViewed(pageNum)) {
                          <i class="bi bi-check me-1"></i>
                        }
                        Page {{ pageNum }}
                      </button>
                    </div>
                  }
                </div>
              </div>
            </div>

            <!-- Signature Fields -->
            <div class="card mb-4">
              <div class="card-header">
                <i class="bi bi-pen me-1"></i>Signature Fields
              </div>
              <div class="card-body">
                @for (field of info()!.fields; track field.id) {
                  <div class="mb-3 p-3 border rounded" [style.border-left]="'4px solid #0d6efd !important'">
                    <label class="form-label fw-semibold">
                      {{ formatFieldType(field.field_type) }}
                      @if (field.required) {
                        <span class="text-danger">*</span>
                      }
                      <span class="text-muted small ms-1">(Page {{ field.page }})</span>
                    </label>
                    @if (field.field_type === 'checkbox') {
                      <div class="form-check">
                        <input
                          type="checkbox"
                          class="form-check-input"
                          [checked]="fieldValues()[field.id] === 'true'"
                          (change)="setFieldValue(field.id, $any($event.target).checked ? 'true' : 'false')"
                        />
                        <label class="form-check-label">I agree</label>
                      </div>
                    } @else if (field.field_type === 'signature' || field.field_type === 'initials') {
                      <div
                        class="border rounded p-4 text-center bg-light"
                        style="cursor: pointer; min-height: 80px;"
                        (click)="setFieldValue(field.id, field.field_type === 'signature' ? info()!.signer_name : getInitials())"
                      >
                        @if (fieldValues()[field.id]) {
                          <span class="fs-4" style="font-family: cursive;">
                            {{ fieldValues()[field.id] }}
                          </span>
                        } @else {
                          <span class="text-muted">Click to {{ field.field_type === 'signature' ? 'sign' : 'initial' }}</span>
                        }
                      </div>
                    } @else {
                      <input
                        type="text"
                        class="form-control"
                        [ngModel]="fieldValues()[field.id] || ''"
                        (ngModelChange)="setFieldValue(field.id, $event)"
                        [placeholder]="formatFieldType(field.field_type)"
                      />
                    }
                  </div>
                }
              </div>
            </div>

            <!-- Actions -->
            <div class="d-flex gap-2">
              <button
                class="btn btn-primary btn-lg flex-grow-1"
                (click)="completeSign()"
                [disabled]="submitting()"
              >
                @if (submitting()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                  Signing...
                } @else {
                  <i class="bi bi-pen me-1"></i>Sign & Complete
                }
              </button>
              <button
                class="btn btn-outline-danger btn-lg"
                (click)="showDecline.set(true)"
                [disabled]="submitting()"
              >
                <i class="bi bi-x-circle me-1"></i>Decline
              </button>
            </div>

            <!-- Decline Modal -->
            @if (showDecline()) {
              <div class="card mt-3 border-danger">
                <div class="card-body">
                  <h6>Decline Signing</h6>
                  <textarea
                    class="form-control mb-2"
                    rows="3"
                    placeholder="Please provide a reason for declining..."
                    [ngModel]="declineReason()"
                    (ngModelChange)="declineReason.set($event)"
                  ></textarea>
                  <div class="d-flex gap-2">
                    <button
                      class="btn btn-danger"
                      (click)="decline()"
                      [disabled]="submitting()"
                    >
                      Confirm Decline
                    </button>
                    <button
                      class="btn btn-outline-secondary"
                      (click)="showDecline.set(false)"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            }

            @if (submitError()) {
              <div class="alert alert-danger mt-3">{{ submitError() }}</div>
            }
          }
        </div>
      </div>
    }
  `,
})
export class PublicSigningComponent implements OnInit {
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
