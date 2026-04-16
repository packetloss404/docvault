import { Component, OnInit, signal, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { DocumentService } from '../../services/document.service';
import { DocumentVersion } from '../../models/document.model';

@Component({
  selector: 'app-version-compare',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="container-fluid py-3">
      <!-- Breadcrumb -->
      <nav aria-label="breadcrumb" class="mb-3">
        <ol class="breadcrumb">
          <li class="breadcrumb-item">
            <a routerLink="/documents">Documents</a>
          </li>
          <li class="breadcrumb-item">
            <a [routerLink]="['/documents', documentId]">Document</a>
          </li>
          <li class="breadcrumb-item active">Version Compare</li>
        </ol>
      </nav>

      <h4 class="mb-3">
        <i class="bi bi-file-diff me-2"></i>Compare Versions
      </h4>

      <!-- Version selectors -->
      <div class="card mb-3">
        <div class="card-body">
          <div class="row g-3 align-items-end">
            <div class="col-md-4">
              <label class="form-label fw-semibold">Version A (from)</label>
              <select
                class="form-select"
                [(ngModel)]="selectedV1"
                [disabled]="versions().length === 0"
              >
                <option [ngValue]="null">Select version...</option>
                @for (ver of versions(); track ver.id) {
                  <option [ngValue]="ver.id">
                    v{{ ver.version_number }}
                    @if (ver.is_active) { (active) }
                    @if (ver.comment) { — {{ ver.comment | slice:0:40 }} }
                  </option>
                }
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label fw-semibold">Version B (to)</label>
              <select
                class="form-select"
                [(ngModel)]="selectedV2"
                [disabled]="versions().length === 0"
              >
                <option [ngValue]="null">Select version...</option>
                @for (ver of versions(); track ver.id) {
                  <option [ngValue]="ver.id">
                    v{{ ver.version_number }}
                    @if (ver.is_active) { (active) }
                    @if (ver.comment) { — {{ ver.comment | slice:0:40 }} }
                  </option>
                }
              </select>
            </div>

            <div class="col-md-4">
              <button
                class="btn btn-primary"
                (click)="compare()"
                [disabled]="!selectedV1 || !selectedV2 || selectedV1 === selectedV2 || comparing()"
              >
                @if (comparing()) {
                  <span class="spinner-border spinner-border-sm me-1" role="status"></span>
                  Comparing...
                } @else {
                  <i class="bi bi-file-diff me-1"></i>Compare
                }
              </button>
            </div>
          </div>

          @if (selectedV1 && selectedV2 && selectedV1 === selectedV2) {
            <div class="alert alert-warning mt-3 mb-0 py-2">
              Please select two different versions to compare.
            </div>
          }
        </div>
      </div>

      <!-- Error -->
      @if (error()) {
        <div class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>{{ error() }}
        </div>
      }

      <!-- Diff result -->
      @if (diffHtml()) {
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <span class="fw-semibold">
              Diff: v{{ compareResult()?.v1?.version_number }} &rarr; v{{ compareResult()?.v2?.version_number }}
            </span>
            <span class="text-muted small">Side-by-side diff</span>
          </div>
          <div class="card-body p-0 overflow-auto">
            <div class="diff-container" [innerHTML]="diffHtml()"></div>
          </div>
        </div>
      } @else if (!comparing() && versions().length === 0) {
        <div class="alert alert-info">
          <i class="bi bi-info-circle me-2"></i>
          This document has no version history yet.
        </div>
      } @else if (!comparing() && !diffHtml()) {
        <div class="text-center text-muted py-5">
          <i class="bi bi-file-diff" style="font-size: 3rem;"></i>
          <p class="mt-2">Select two versions above and click Compare.</p>
        </div>
      }
    </div>

    <style>
      .diff-container :host ::ng-deep table.diff {
        width: 100%;
        border-collapse: collapse;
        font-family: monospace;
        font-size: 0.85rem;
      }
      .diff-container :host ::ng-deep td {
        padding: 2px 6px;
        white-space: pre-wrap;
        word-break: break-all;
      }
      .diff-container :host ::ng-deep .diff_header {
        background-color: #f8f9fa;
        font-weight: bold;
      }
      .diff-container :host ::ng-deep .diff_next { display: none; }
      .diff-container :host ::ng-deep .diff_add { background-color: #d4edda; }
      .diff-container :host ::ng-deep .diff_chg { background-color: #fff3cd; }
      .diff-container :host ::ng-deep .diff_sub { background-color: #f8d7da; }
    </style>
  `,
})
export class VersionCompareComponent implements OnInit {
  @Input() documentId!: number;

  versions = signal<DocumentVersion[]>([]);
  comparing = signal(false);
  diffHtml = signal<SafeHtml | null>(null);
  error = signal<string | null>(null);
  compareResult = signal<{ v1: DocumentVersion; v2: DocumentVersion } | null>(null);

  selectedV1: number | null = null;
  selectedV2: number | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private documentService: DocumentService,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    // Support both @Input() and route param
    const routeId = Number(this.route.snapshot.paramMap.get('id'));
    if (routeId && !this.documentId) {
      this.documentId = routeId;
    }

    if (this.documentId) {
      this.loadVersions();
    }
  }

  loadVersions(): void {
    this.documentService.getVersions(this.documentId).subscribe({
      next: (versions) => {
        this.versions.set(versions);
        // Pre-select latest two versions if available
        if (versions.length >= 2) {
          this.selectedV2 = versions[0].id;
          this.selectedV1 = versions[1].id;
        }
      },
      error: () => {
        this.error.set('Failed to load version history.');
      },
    });
  }

  compare(): void {
    if (!this.selectedV1 || !this.selectedV2) return;
    if (this.selectedV1 === this.selectedV2) return;

    this.comparing.set(true);
    this.error.set(null);
    this.diffHtml.set(null);

    this.documentService
      .compareVersions(this.documentId, this.selectedV1, this.selectedV2)
      .subscribe({
        next: (result) => {
          this.compareResult.set({ v1: result.v1, v2: result.v2 });
          this.diffHtml.set(this.sanitizer.bypassSecurityTrustHtml(result.diff_html));
          this.comparing.set(false);
        },
        error: (err) => {
          this.error.set(
            err?.error?.error ?? 'Failed to compare versions. Please try again.',
          );
          this.comparing.set(false);
        },
      });
  }
}
