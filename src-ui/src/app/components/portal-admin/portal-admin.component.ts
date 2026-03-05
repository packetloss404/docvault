import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PortalService } from '../../services/portal.service';
import { PortalConfig } from '../../models/portal.model';

@Component({
  selector: 'app-portal-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="container-fluid">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h4 class="mb-0"><i class="bi bi-door-open me-2"></i>Contributor Portals</h4>
        <button class="btn btn-primary btn-sm" (click)="showForm.set(!showForm())">
          <i class="bi" [ngClass]="showForm() ? 'bi-x' : 'bi-plus'"></i>
          {{ showForm() ? 'Cancel' : 'Create Portal' }}
        </button>
      </div>

      <!-- Create/Edit Form -->
      @if (showForm()) {
        <div class="card mb-4">
          <div class="card-header">
            {{ editingPortal() ? 'Edit Portal' : 'New Portal' }}
          </div>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Name</label>
                <input
                  type="text"
                  class="form-control form-control-sm"
                  [ngModel]="formName()"
                  (ngModelChange)="formName.set($event)"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label">Slug</label>
                <input
                  type="text"
                  class="form-control form-control-sm"
                  [ngModel]="formSlug()"
                  (ngModelChange)="formSlug.set($event)"
                  placeholder="auto-generated if blank"
                />
              </div>
              <div class="col-12">
                <label class="form-label">Welcome Text</label>
                <textarea
                  class="form-control form-control-sm"
                  rows="3"
                  [ngModel]="formWelcomeText()"
                  (ngModelChange)="formWelcomeText.set($event)"
                ></textarea>
              </div>
              <div class="col-md-4">
                <label class="form-label">Primary Color</label>
                <input
                  type="color"
                  class="form-control form-control-sm form-control-color"
                  [ngModel]="formPrimaryColor()"
                  (ngModelChange)="formPrimaryColor.set($event)"
                />
              </div>
              <div class="col-md-4">
                <label class="form-label">Max File Size (MB)</label>
                <input
                  type="number"
                  class="form-control form-control-sm"
                  [ngModel]="formMaxFileSize()"
                  (ngModelChange)="formMaxFileSize.set($event)"
                />
              </div>
              <div class="col-md-4">
                <label class="form-label">Default Document Type ID</label>
                <input
                  type="number"
                  class="form-control form-control-sm"
                  [ngModel]="formDefaultDocType()"
                  (ngModelChange)="formDefaultDocType.set($event)"
                  placeholder="Optional"
                />
              </div>
              <div class="col-md-4">
                <div class="form-check mt-4">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="reqEmail"
                    [ngModel]="formRequireEmail()"
                    (ngModelChange)="formRequireEmail.set($event)"
                  />
                  <label class="form-check-label" for="reqEmail">Require Email</label>
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-check mt-4">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="reqName"
                    [ngModel]="formRequireName()"
                    (ngModelChange)="formRequireName.set($event)"
                  />
                  <label class="form-check-label" for="reqName">Require Name</label>
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-check mt-4">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="isActive"
                    [ngModel]="formIsActive()"
                    (ngModelChange)="formIsActive.set($event)"
                  />
                  <label class="form-check-label" for="isActive">Active</label>
                </div>
              </div>
            </div>
            @if (formError()) {
              <div class="alert alert-danger mt-3 mb-0 py-2 small">{{ formError() }}</div>
            }
            <div class="mt-3">
              <button class="btn btn-primary btn-sm" (click)="savePortal()" [disabled]="!formName()">
                <i class="bi bi-check me-1"></i>{{ editingPortal() ? 'Update' : 'Create' }}
              </button>
              <button class="btn btn-outline-secondary btn-sm ms-2" (click)="cancelForm()">Cancel</button>
            </div>
          </div>
        </div>
      }

      <!-- Portal List -->
      @if (loading()) {
        <div class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      } @else if (portals().length === 0) {
        <div class="text-center text-muted py-4">
          <i class="bi bi-door-open fs-1"></i>
          <p class="mt-2">No contributor portals configured yet.</p>
        </div>
      } @else {
        <div class="table-responsive">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
                <th>Active</th>
                <th>Created</th>
                <th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (portal of portals(); track portal.id) {
                <tr>
                  <td>
                    <span
                      class="d-inline-block rounded-circle me-2"
                      [style.width.px]="12"
                      [style.height.px]="12"
                      [style.background]="portal.primary_color"
                    ></span>
                    {{ portal.name }}
                  </td>
                  <td><code>{{ portal.slug }}</code></td>
                  <td>
                    <span
                      class="badge"
                      [class.bg-success]="portal.is_active"
                      [class.bg-secondary]="!portal.is_active"
                    >
                      {{ portal.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>{{ portal.created_at | date: 'short' }}</td>
                  <td class="text-end">
                    <a
                      [href]="'/portal/' + portal.slug"
                      target="_blank"
                      class="btn btn-outline-info btn-sm me-1"
                      title="Open public portal"
                    >
                      <i class="bi bi-box-arrow-up-right"></i>
                    </a>
                    <button
                      class="btn btn-outline-primary btn-sm me-1"
                      (click)="editPortal(portal)"
                      title="Edit"
                    >
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button
                      class="btn btn-outline-danger btn-sm"
                      (click)="deletePortal(portal)"
                      title="Delete"
                    >
                      <i class="bi bi-trash"></i>
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class PortalAdminComponent implements OnInit {
  portals = signal<PortalConfig[]>([]);
  loading = signal(true);
  showForm = signal(false);
  editingPortal = signal<PortalConfig | null>(null);
  formError = signal('');

  formName = signal('');
  formSlug = signal('');
  formWelcomeText = signal('');
  formPrimaryColor = signal('#0d6efd');
  formMaxFileSize = signal(25);
  formDefaultDocType = signal<number | null>(null);
  formRequireEmail = signal(true);
  formRequireName = signal(false);
  formIsActive = signal(true);

  constructor(private portalService: PortalService) {}

  ngOnInit(): void {
    this.loadPortals();
  }

  loadPortals(): void {
    this.loading.set(true);
    this.portalService.getPortals().subscribe({
      next: (resp) => {
        this.portals.set(resp.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  editPortal(portal: PortalConfig): void {
    this.editingPortal.set(portal);
    this.formName.set(portal.name);
    this.formSlug.set(portal.slug);
    this.formWelcomeText.set(portal.welcome_text);
    this.formPrimaryColor.set(portal.primary_color);
    this.formMaxFileSize.set(portal.max_file_size_mb);
    this.formDefaultDocType.set(portal.default_document_type);
    this.formRequireEmail.set(portal.require_email);
    this.formRequireName.set(portal.require_name);
    this.formIsActive.set(portal.is_active);
    this.showForm.set(true);
    this.formError.set('');
  }

  cancelForm(): void {
    this.showForm.set(false);
    this.editingPortal.set(null);
    this.resetForm();
  }

  private resetForm(): void {
    this.formName.set('');
    this.formSlug.set('');
    this.formWelcomeText.set('');
    this.formPrimaryColor.set('#0d6efd');
    this.formMaxFileSize.set(25);
    this.formDefaultDocType.set(null);
    this.formRequireEmail.set(true);
    this.formRequireName.set(false);
    this.formIsActive.set(true);
    this.formError.set('');
  }

  savePortal(): void {
    this.formError.set('');
    const data: Partial<PortalConfig> = {
      name: this.formName(),
      slug: this.formSlug() || undefined,
      welcome_text: this.formWelcomeText(),
      primary_color: this.formPrimaryColor(),
      max_file_size_mb: this.formMaxFileSize(),
      default_document_type: this.formDefaultDocType(),
      require_email: this.formRequireEmail(),
      require_name: this.formRequireName(),
      is_active: this.formIsActive(),
    };

    const editing = this.editingPortal();
    const obs = editing
      ? this.portalService.updatePortal(editing.id, data)
      : this.portalService.createPortal(data);

    obs.subscribe({
      next: () => {
        this.cancelForm();
        this.loadPortals();
      },
      error: (err) => {
        this.formError.set(
          err.error?.detail || JSON.stringify(err.error) || 'Save failed.',
        );
      },
    });
  }

  deletePortal(portal: PortalConfig): void {
    if (!confirm(`Delete portal "${portal.name}"? This cannot be undone.`)) return;
    this.portalService.deletePortal(portal.id).subscribe({
      next: () => this.loadPortals(),
    });
  }
}
