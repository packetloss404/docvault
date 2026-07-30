import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { Group, Permission } from '../../models/security.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-admin-groups',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  styleUrl: './admin-groups.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <div class="dv-pagehead">
          <h1 class="dv-h1 dv-h1--sm">Admin</h1>
          <dv-subnav />
          <button type="button" class="dv-btn dv-btn--primary dv-push" (click)="startCreate()">
            + New group
          </button>
        </div>

        @if (errorMessage()) {
          <div class="ag-banner ag-banner--error" role="alert">
            <span>{{ errorMessage() }}</span>
            <button
              type="button"
              class="ag-banner__close"
              aria-label="Dismiss"
              (click)="errorMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        @if (successMessage()) {
          <div class="ag-banner ag-banner--ok" role="status">
            <span>{{ successMessage() }}</span>
            <button
              type="button"
              class="ag-banner__close"
              aria-label="Dismiss"
              (click)="successMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        <!-- Create / Edit form -->
        @if (showForm()) {
          <div class="dv-card dv-card--pad dv-card--accent ag-form">
            <div class="dv-card__title">{{ editing() ? 'Edit group' : 'New group' }}</div>

            <div class="ag-form__row">
              <div>
                <label class="dv-field__label" for="ag-name">group name *</label>
                <input
                  id="ag-name"
                  type="text"
                  class="dv-input"
                  [(ngModel)]="formName"
                  placeholder="e.g. Editors, Viewers, Admins"
                />
              </div>
            </div>

            <div class="ag-perms">
              <span class="dv-field__label">permissions</span>
              @if (permissions().length === 0) {
                <span class="dv-meta">No permissions available.</span>
              } @else {
                <div class="dv-well ag-perms__box">
                  @for (perm of permissions(); track perm.id) {
                    <label class="ag-check" [for]="'perm-' + perm.id">
                      <input
                        class="dv-checkbox"
                        type="checkbox"
                        [id]="'perm-' + perm.id"
                        [checked]="formPermissions.includes(perm.id)"
                        (change)="togglePermission(perm.id, $event)"
                      />
                      <span>{{ perm.name }}</span>
                    </label>
                  }
                </div>
              }
            </div>

            <div class="ag-form__actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--md"
                (click)="save()"
                [disabled]="saving() || !formName.trim()"
              >
                @if (saving()) {
                  <span class="dv-spinner"></span>
                }
                {{ editing() ? 'Save changes' : 'Create group' }}
              </button>
              <button type="button" class="dv-btn dv-btn--ghost dv-btn--md" (click)="cancelForm()">
                Cancel
              </button>
            </div>
          </div>
        }

        <!-- Groups -->
        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading groups…</div>
        } @else if (groups().length === 0) {
          <div class="dv-empty">No groups defined yet.</div>
        } @else {
          <div class="ag-list">
            @for (group of groups(); track group.id) {
              <div class="dv-card dv-card--r10 ag-row">
                <span class="ag-row__name">{{ group.name }}</span>
                <span class="dv-chip dv-chip--well dv-push">
                  @if (group.permissions.length === 0) {
                    no permissions
                  } @else {
                    {{ group.permissions.length }} permission{{
                      group.permissions.length !== 1 ? 's' : ''
                    }}
                  }
                </span>
                <span class="ag-actions">
                  <button type="button" class="ag-action" (click)="startEdit(group)">edit</button>
                  <button
                    type="button"
                    class="ag-action ag-action--danger"
                    (click)="deleteGroup(group)"
                  >
                    del
                  </button>
                </span>
              </div>
            }
          </div>
        }
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
