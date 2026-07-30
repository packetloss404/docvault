import { Component, OnInit, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { DocumentService } from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';
import { DocumentType } from '../../models/document.model';
import {
  CustomField,
  DocumentTypeCustomField,
} from '../../models/organization.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-doctype-editor',
  standalone: true,
  imports: [FormsModule, RouterLink, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner">
        <dv-subnav>
          <a
            subnavAction
            class="dv-btn dv-btn--secondary dv-btn--sm dv-push tabstrip-action"
            routerLink="/metadata-types"
            >← Back</a
          >
        </dv-subnav>

        <div class="dv-pagehead pagehead">
          <h1 class="dv-h1 dv-h1--sm">
            @if (loading()) {
              <span class="dv-faint">Loading…</span>
            } @else if (docType()) {
              {{ docType()!.name }}
            } @else {
              Document type not found
            }
          </h1>
          @if (!loading() && docType()) {
            <span class="dv-chip dv-chip--upper">custom fields</span>
          }
        </div>

        @if (error()) {
          <div class="form-error" role="alert">{{ error() }}</div>
        }

        @if (!loading() && docType()) {
          <!-- Assigned custom fields -->
          <div class="dv-card dv-card--flush stack">
            <div class="dv-card__head">
              <span class="dv-card__title">Assigned custom fields</span>
              <span class="dv-ts dv-push">{{ assignments().length }}</span>
            </div>

            @if (assignments().length === 0) {
              <div class="dv-empty">No custom fields assigned yet.</div>
            }

            @for (a of assignments(); track a.id) {
              <div class="dv-listrow">
                <span class="row-name">{{ a.field_name }}</span>
                <span class="dv-chip">{{ a.field_data_type }}</span>
                @if (a.required) {
                  <span class="dv-chip dv-chip--danger dv-chip--upper">required</span>
                }
                <button
                  type="button"
                  class="dv-btn dv-btn--danger dv-btn--sm dv-push"
                  (click)="removeAssignment(a)"
                  [disabled]="saving()"
                >
                  Remove
                </button>
              </div>
            }
          </div>

          <!-- Add custom field -->
          <div class="dv-card dv-card--pad stack form-card">
            <div class="dv-card__title">Add custom field</div>

            @if (availableFields().length === 0) {
              <p class="dv-muted form-note">
                All available custom fields are already assigned, or no custom fields exist.
              </p>
            } @else {
              <div class="form-grid">
                <div>
                  <label class="dv-field__label" for="dte-field">custom field</label>
                  <select id="dte-field" class="dv-select" [(ngModel)]="selectedFieldId">
                    <option [ngValue]="null">— select a field —</option>
                    @for (f of availableFields(); track f.id) {
                      <option [ngValue]="f.id">{{ f.name }} ({{ f.data_type }})</option>
                    }
                  </select>
                </div>

                <div class="form-switch">
                  <span class="dv-field__label">required</span>
                  <button
                    type="button"
                    class="dv-toggle"
                    [class.is-on]="addRequired"
                    [attr.aria-pressed]="addRequired"
                    aria-label="Required"
                    (click)="addRequired = !addRequired"
                  ></button>
                </div>

                <div class="form-submit">
                  <button
                    type="button"
                    class="dv-btn dv-btn--primary dv-btn--sm dv-btn--block"
                    (click)="addAssignment()"
                    [disabled]="selectedFieldId === null || saving()"
                  >
                    @if (saving()) {
                      Adding…
                    } @else {
                      Add field
                    }
                  </button>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
  styleUrl: './doctype-editor.component.scss',
})
export class DoctypeEditorComponent implements OnInit {
  docType = signal<DocumentType | null>(null);
  assignments = signal<DocumentTypeCustomField[]>([]);
  allFields = signal<CustomField[]>([]);
  loading = signal(true);
  saving = signal(false);
  error = signal<string | null>(null);

  selectedFieldId: number | null = null;
  addRequired = false;

  /** Fields not already assigned to this doc type */
  availableFields = computed(() => {
    const assignedIds = new Set(this.assignments().map((a) => a.custom_field));
    return this.allFields().filter((f) => !assignedIds.has(f.id));
  });

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private docService: DocumentService,
    private orgService: OrganizationService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) {
      this.router.navigate(['/metadata-types']);
      return;
    }
    this.loadAll(id);
  }

  private get docTypeId(): number {
    return this.docType()?.id ?? 0;
  }

  loadAll(id: number): void {
    this.loading.set(true);
    this.error.set(null);

    forkJoin({
      docType: this.docService.getDocumentType(id),
      assignments: this.orgService.getDocTypeCustomFields(id),
      allFields: this.orgService.getCustomFields(),
    }).subscribe({
      next: ({ docType, assignments, allFields }) => {
        this.docType.set(docType);
        this.assignments.set(assignments);
        this.allFields.set(allFields.results);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(
          err?.error?.detail ?? 'Failed to load document type data.',
        );
        this.loading.set(false);
      },
    });
  }

  addAssignment(): void {
    if (this.selectedFieldId === null) return;
    this.saving.set(true);
    this.error.set(null);

    this.orgService
      .assignDocTypeCustomField(this.docTypeId, this.selectedFieldId, this.addRequired)
      .subscribe({
        next: (assignment) => {
          this.assignments.update((list) => [...list, assignment]);
          this.selectedFieldId = null;
          this.addRequired = false;
          this.saving.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Failed to assign custom field.');
          this.saving.set(false);
        },
      });
  }

  removeAssignment(assignment: DocumentTypeCustomField): void {
    if (!confirm(`Remove field "${assignment.field_name}" from this document type?`)) return;
    this.saving.set(true);
    this.error.set(null);

    this.orgService
      .removeDocTypeCustomField(this.docTypeId, assignment.id)
      .subscribe({
        next: () => {
          this.assignments.update((list) => list.filter((a) => a.id !== assignment.id));
          this.saving.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Failed to remove custom field.');
          this.saving.set(false);
        },
      });
  }
}
