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
    <div class="dv-screen dv-screen--tight">
      <div class="dv-crumb vc__crumb">
        <a class="dv-crumb__up" routerLink="/documents">documents /</a>
        <a class="dv-crumb__up" [routerLink]="['/documents', documentId]"
          >document /</a
        >
        <span>compare versions</span>
      </div>

      <div class="dv-inner vc">
        <!-- Version selectors -->
        <div class="dv-card dv-card--r10 vc__picker">
          <div class="vc__pickrow">
            <div class="vc__field">
              <label class="dv-field__label" for="vc-a">version a (from)</label>
              <select
                id="vc-a"
                class="dv-input dv-input--r7 vc__select"
                [(ngModel)]="selectedV1"
                [disabled]="versions().length === 0"
              >
                <option [ngValue]="null">select version…</option>
                @for (ver of versions(); track ver.id) {
                  <option [ngValue]="ver.id">
                    v{{ ver.version_number }}
                    @if (ver.is_active) { (active) }
                    @if (ver.comment) { — {{ ver.comment | slice: 0 : 40 }} }
                  </option>
                }
              </select>
            </div>

            <div class="vc__field">
              <label class="dv-field__label" for="vc-b">version b (to)</label>
              <select
                id="vc-b"
                class="dv-input dv-input--r7 vc__select"
                [(ngModel)]="selectedV2"
                [disabled]="versions().length === 0"
              >
                <option [ngValue]="null">select version…</option>
                @for (ver of versions(); track ver.id) {
                  <option [ngValue]="ver.id">
                    v{{ ver.version_number }}
                    @if (ver.is_active) { (active) }
                    @if (ver.comment) { — {{ ver.comment | slice: 0 : 40 }} }
                  </option>
                }
              </select>
            </div>

            <button
              class="dv-btn dv-btn--primary dv-btn--md vc__go"
              (click)="compare()"
              [disabled]="
                !selectedV1 ||
                !selectedV2 ||
                selectedV1 === selectedV2 ||
                comparing()
              "
            >
              @if (comparing()) {
                <span class="dv-spinner"></span>
                Comparing…
              } @else {
                Compare
              }
            </button>
          </div>

          @if (selectedV1 && selectedV2 && selectedV1 === selectedV2) {
            <div class="dv-warn vc__note">
              Select two different versions to compare.
            </div>
          }
        </div>

        @if (error()) {
          <div class="dv-card dv-card--r10 vc__error" role="alert">
            {{ error() }}
          </div>
        }

        <!-- Diff result -->
        @if (diffHtml()) {
          <div class="vc__result">
            <div class="vc__resulthead">
              <span class="dv-mono vc__versions">
                v{{ compareResult()?.v1?.version_number }} →
                v{{ compareResult()?.v2?.version_number }}
              </span>
              <span class="dv-meta dv-push">side-by-side</span>
            </div>
            <div class="dv-well vc__pane">
              <div class="vc__diff" [innerHTML]="diffHtml()"></div>
            </div>
            <div class="vc__legend">
              <span class="dv-meta dv-ok">+ added</span>
              <span class="dv-meta dv-danger">− removed</span>
              <span class="dv-meta dv-warn">~ changed</span>
            </div>
          </div>
        } @else if (!comparing() && versions().length === 0) {
          <div class="dv-empty">This document has no version history yet.</div>
        } @else if (!comparing() && !diffHtml()) {
          <div class="dv-empty">
            Select two versions above and choose Compare.
          </div>
        }
      </div>
    </div>
  `,
  styleUrl: './version-compare.component.scss',
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
