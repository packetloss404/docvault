import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';
import { DocumentService } from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';
import { DocumentType } from '../../models/document.model';
import {
  CustomField,
  DocumentTypeCustomField,
} from '../../models/organization.model';

@Component({
  selector: 'app-doctype-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="container py-4">
      <!-- Header -->
      <div class="d-flex align-items-center mb-4 gap-3">
        <a routerLink="/metadata-types" class="btn btn-outline-secondary btn-sm">
          &larr; Back
        </a>
        <h2 class="mb-0">
          @if (loading()) {
            <span class="text-muted">Loading&hellip;</span>
          } @else if (docType()) {
            {{ docType()!.name }} &mdash; Custom Fields
          } @else {
            Document Type Not Found
          }
        </h2>
      </div>

      @if (error()) {
        <div class="alert alert-danger">{{ error() }}</div>
      }

      @if (!loading() && docType()) {
        <!-- Assigned custom fields list -->
        <div class="card mb-4">
          <div class="card-header fw-semibold">Assigned Custom Fields</div>
          <ul class="list-group list-group-flush">
            @if (assignments().length === 0) {
              <li class="list-group-item text-muted fst-italic">
                No custom fields assigned yet.
              </li>
            }
            @for (a of assignments(); track a.id) {
              <li class="list-group-item d-flex align-items-center justify-content-between">
                <div>
                  <span class="fw-medium">{{ a.field_name }}</span>
                  <span class="badge bg-secondary ms-2">{{ a.field_data_type }}</span>
                  @if (a.required) {
                    <span class="badge bg-danger ms-1">Required</span>
                  }
                </div>
                <button
                  class="btn btn-outline-danger btn-sm"
                  (click)="removeAssignment(a)"
                  [disabled]="saving()"
                >
                  Remove
                </button>
              </li>
            }
          </ul>
        </div>

        <!-- Add custom field -->
        <div class="card">
          <div class="card-header fw-semibold">Add Custom Field</div>
          <div class="card-body">
            @if (availableFields().length === 0) {
              <p class="text-muted mb-0">
                All available custom fields are already assigned, or no custom fields exist.
              </p>
            } @else {
              <div class="row g-3 align-items-end">
                <div class="col-sm-5">
                  <label class="form-label">Custom Field</label>
                  <select
                    class="form-select"
                    [(ngModel)]="selectedFieldId"
                  >
                    <option [ngValue]="null">— Select a field —</option>
                    @for (f of availableFields(); track f.id) {
                      <option [ngValue]="f.id">{{ f.name }} ({{ f.data_type }})</option>
                    }
                  </select>
                </div>
                <div class="col-sm-3 d-flex align-items-center gap-2 pt-3">
                  <input
                    type="checkbox"
                    class="form-check-input"
                    id="requiredCheck"
                    [(ngModel)]="addRequired"
                  />
                  <label class="form-check-label" for="requiredCheck">Required</label>
                </div>
                <div class="col-sm-4">
                  <button
                    class="btn btn-primary w-100"
                    (click)="addAssignment()"
                    [disabled]="selectedFieldId === null || saving()"
                  >
                    @if (saving()) {
                      Adding&hellip;
                    } @else {
                      Add Field
                    }
                  </button>
                </div>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
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
