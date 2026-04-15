import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { Group, Permission } from '../../models/security.model';

@Component({
  selector: 'app-admin-groups',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container-fluid py-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0"><i class="bi bi-collection me-2"></i>Group Management</h2>
        <button class="btn btn-primary" (click)="startCreate()">
          <i class="bi bi-plus-lg me-1"></i> New Group
        </button>
      </div>

      @if (errorMessage()) {
        <div class="alert alert-danger alert-dismissible">
          {{ errorMessage() }}
          <button type="button" class="btn-close" (click)="errorMessage.set('')"></button>
        </div>
      }

      @if (successMessage()) {
        <div class="alert alert-success alert-dismissible">
          {{ successMessage() }}
          <button type="button" class="btn-close" (click)="successMessage.set('')"></button>
        </div>
      }

      <!-- Create / Edit Form -->
      @if (showForm()) {
        <div class="card mb-4 border-primary">
          <div class="card-header bg-primary text-white">
            <h5 class="mb-0">{{ editing() ? 'Edit Group' : 'Create Group' }}</h5>
          </div>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Group Name <span class="text-danger">*</span></label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formName"
                  placeholder="e.g. Editors, Viewers, Admins"
                />
              </div>
              <div class="col-12">
                <label class="form-label">Permissions</label>
                @if (permissions().length === 0) {
                  <p class="text-muted small mb-0">No permissions available.</p>
                } @else {
                  <div class="border rounded p-2" style="max-height: 250px; overflow-y: auto;">
                    <div class="row g-1">
                      @for (perm of permissions(); track perm.id) {
                        <div class="col-md-4">
                          <div class="form-check">
                            <input
                              class="form-check-input"
                              type="checkbox"
                              [id]="'perm-' + perm.id"
                              [checked]="formPermissions.includes(perm.id)"
                              (change)="togglePermission(perm.id, $event)"
                            />
                            <label class="form-check-label small" [for]="'perm-' + perm.id">
                              {{ perm.name }}
                            </label>
                          </div>
                        </div>
                      }
                    </div>
                  </div>
                }
              </div>
            </div>
            <div class="mt-3 d-flex gap-2">
              <button
                class="btn btn-primary"
                (click)="save()"
                [disabled]="saving() || !formName.trim()"
              >
                @if (saving()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                }
                {{ editing() ? 'Save Changes' : 'Create Group' }}
              </button>
              <button class="btn btn-outline-secondary" (click)="cancelForm()">Cancel</button>
            </div>
          </div>
        </div>
      }

      <!-- Groups Table -->
      <div class="card">
        <div class="card-header">
          <h5 class="mb-0">Groups</h5>
        </div>
        <div class="card-body p-0">
          @if (loading()) {
            <div class="text-center py-5">
              <div class="spinner-border text-primary"></div>
              <p class="mt-2 text-muted">Loading groups…</p>
            </div>
          } @else if (groups().length === 0) {
            <div class="text-center py-5 text-muted">
              <i class="bi bi-collection fs-1 d-block mb-2"></i>
              No groups defined yet.
            </div>
          } @else {
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                  <tr>
                    <th>Name</th>
                    <th>Permissions</th>
                    <th class="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (group of groups(); track group.id) {
                    <tr>
                      <td><strong>{{ group.name }}</strong></td>
                      <td>
                        @if (group.permissions.length === 0) {
                          <span class="text-muted small">None</span>
                        } @else {
                          <span class="badge bg-info text-dark me-1">
                            {{ group.permissions.length }} permission{{ group.permissions.length !== 1 ? 's' : '' }}
                          </span>
                        }
                      </td>
                      <td class="text-end">
                        <button
                          class="btn btn-sm btn-outline-primary me-1"
                          (click)="startEdit(group)"
                        >
                          <i class="bi bi-pencil"></i>
                        </button>
                        <button
                          class="btn btn-sm btn-outline-danger"
                          (click)="deleteGroup(group)"
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
      </div>
    </div>
  `,
})
export class AdminGroupsComponent implements OnInit {
  groups = signal<Group[]>([]);
  permissions = signal<Permission[]>([]);
  loading = signal(false);
  saving = signal(false);
  showForm = signal(false);
  editing = signal<Group | null>(null);
  errorMessage = signal('');
  successMessage = signal('');

  // Form fields
  formName = '';
  formPermissions: number[] = [];

  constructor(private securityService: SecurityService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.securityService.getGroups().subscribe({
      next: (groups) => {
        this.groups.set(groups);
        this.loading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to load groups.');
        this.loading.set(false);
      },
    });
    this.securityService.getPermissions().subscribe({
      next: (perms) => this.permissions.set(perms),
    });
  }

  startCreate(): void {
    this.editing.set(null);
    this.formName = '';
    this.formPermissions = [];
    this.showForm.set(true);
  }

  startEdit(group: Group): void {
    this.editing.set(group);
    this.formName = group.name;
    this.formPermissions = [...group.permissions];
    this.showForm.set(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelForm(): void {
    this.showForm.set(false);
    this.editing.set(null);
  }

  togglePermission(id: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.formPermissions = [...this.formPermissions, id];
    } else {
      this.formPermissions = this.formPermissions.filter((p) => p !== id);
    }
  }

  save(): void {
    const data: Partial<Group> = {
      name: this.formName.trim(),
      permissions: this.formPermissions,
    };

    this.saving.set(true);
    this.errorMessage.set('');

    const editingGroup = this.editing();
    const request = editingGroup
      ? this.securityService.updateGroup(editingGroup.id, data)
      : this.securityService.createGroup(data);

    request.subscribe({
      next: () => {
        this.successMessage.set(editingGroup ? 'Group updated.' : 'Group created.');
        this.saving.set(false);
        this.cancelForm();
        this.load();
      },
      error: () => {
        this.errorMessage.set(editingGroup ? 'Failed to update group.' : 'Failed to create group.');
        this.saving.set(false);
      },
    });
  }

  deleteGroup(group: Group): void {
    if (!confirm(`Delete group "${group.name}"? Users in this group will lose associated permissions.`)) return;
    this.securityService.deleteGroup(group.id).subscribe({
      next: () => {
        this.successMessage.set(`Group "${group.name}" deleted.`);
        this.load();
      },
      error: () => {
        this.errorMessage.set('Failed to delete group.');
      },
    });
  }
}
