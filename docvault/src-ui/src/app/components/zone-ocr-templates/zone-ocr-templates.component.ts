import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import { ZoneOCRTemplate } from '../../models/zone-ocr.model';

@Component({
  selector: 'app-zone-ocr-templates',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Zone OCR Templates</h2>
      <button class="btn btn-primary" (click)="showForm = !showForm">
        <i class="bi bi-plus-lg me-1"></i>
        {{ showForm ? 'Cancel' : 'New Template' }}
      </button>
    </div>

    @if (showForm) {
      <div class="card mb-4">
        <div class="card-body">
          <h5 class="card-title">{{ editingId ? 'Edit' : 'Create' }} Template</h5>
          <form (ngSubmit)="onSave()">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Name</label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formName"
                  name="name"
                  required
                />
              </div>
              <div class="col-md-3">
                <label class="form-label">Page Number</label>
                <input
                  type="number"
                  class="form-control"
                  [(ngModel)]="formPageNumber"
                  name="pageNumber"
                  min="1"
                />
              </div>
              <div class="col-md-3 d-flex align-items-end">
                <div class="form-check form-switch">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    [(ngModel)]="formIsActive"
                    name="isActive"
                    id="activeSwitch"
                  />
                  <label class="form-check-label" for="activeSwitch">Active</label>
                </div>
              </div>
              <div class="col-12">
                <label class="form-label">Description</label>
                <textarea
                  class="form-control"
                  [(ngModel)]="formDescription"
                  name="description"
                  rows="2"
                ></textarea>
              </div>
              <div class="col-12">
                <button type="submit" class="btn btn-success me-2" [disabled]="saving()">
                  <i class="bi bi-check-lg me-1"></i>{{ editingId ? 'Update' : 'Create' }}
                </button>
                <button type="button" class="btn btn-secondary" (click)="cancelEdit()">Cancel</button>
              </div>
            </div>
          </form>
        </div>
      </div>
    }

    @if (loading()) {
      <div class="text-center py-5">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else {
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Page</th>
              <th>Fields</th>
              <th>Status</th>
              <th>Created</th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (template of templates(); track template.id) {
              <tr>
                <td>
                  <a [routerLink]="['/zone-ocr', template.id]" class="fw-semibold text-decoration-none">
                    {{ template.name }}
                  </a>
                </td>
                <td class="text-muted">{{ template.description | slice:0:60 }}{{ template.description.length > 60 ? '...' : '' }}</td>
                <td>{{ template.page_number }}</td>
                <td>
                  <span class="badge bg-secondary">{{ template.field_count }}</span>
                </td>
                <td>
                  @if (template.is_active) {
                    <span class="badge bg-success">Active</span>
                  } @else {
                    <span class="badge bg-warning text-dark">Inactive</span>
                  }
                </td>
                <td>{{ template.created_at | date:'shortDate' }}</td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-primary me-1" (click)="onEdit(template)" title="Edit">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" (click)="onDelete(template)" title="Delete">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="text-center text-muted py-4">
                  No Zone OCR templates found. Create one to get started.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }

    @if (deleteConfirm) {
      <div class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.5);">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Confirm Delete</h5>
              <button type="button" class="btn-close" (click)="deleteConfirm = null"></button>
            </div>
            <div class="modal-body">
              <p>Are you sure you want to delete template <strong>{{ deleteConfirm.name }}</strong>?</p>
              <p class="text-muted">This will also delete all associated fields and results.</p>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" (click)="deleteConfirm = null">Cancel</button>
              <button type="button" class="btn btn-danger" (click)="confirmDelete()">
                <i class="bi bi-trash me-1"></i>Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    }
  `,
})
export class ZoneOcrTemplatesComponent implements OnInit {
  templates = signal<ZoneOCRTemplate[]>([]);
  loading = signal(true);
  saving = signal(false);

  showForm = false;
  editingId: number | null = null;
  formName = '';
  formDescription = '';
  formPageNumber = 1;
  formIsActive = true;
  deleteConfirm: ZoneOCRTemplate | null = null;

  constructor(private zoneOcrService: ZoneOCRService) {}

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.zoneOcrService.getTemplates().subscribe({
      next: (response) => {
        this.templates.set(response.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onEdit(template: ZoneOCRTemplate): void {
    this.editingId = template.id;
    this.formName = template.name;
    this.formDescription = template.description;
    this.formPageNumber = template.page_number;
    this.formIsActive = template.is_active;
    this.showForm = true;
  }

  cancelEdit(): void {
    this.editingId = null;
    this.formName = '';
    this.formDescription = '';
    this.formPageNumber = 1;
    this.formIsActive = true;
    this.showForm = false;
  }

  onSave(): void {
    if (!this.formName.trim()) return;
    this.saving.set(true);
    const data: Partial<ZoneOCRTemplate> = {
      name: this.formName.trim(),
      description: this.formDescription.trim(),
      page_number: this.formPageNumber,
      is_active: this.formIsActive,
    };

    const request = this.editingId
      ? this.zoneOcrService.updateTemplate(this.editingId, data)
      : this.zoneOcrService.createTemplate(data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.cancelEdit();
        this.loadTemplates();
      },
      error: () => this.saving.set(false),
    });
  }

  onDelete(template: ZoneOCRTemplate): void {
    this.deleteConfirm = template;
  }

  confirmDelete(): void {
    if (!this.deleteConfirm) return;
    this.zoneOcrService.deleteTemplate(this.deleteConfirm.id).subscribe({
      next: () => {
        this.deleteConfirm = null;
        this.loadTemplates();
      },
    });
  }
}
