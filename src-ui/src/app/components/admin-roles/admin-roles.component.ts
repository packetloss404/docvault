import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { Role, Permission } from '../../models/security.model';
import { SubnavComponent } from '../subnav/subnav.component';

/** Permission chips shown on a role card before collapsing into "+N more". */
const ROLE_CHIP_LIMIT = 6;

@Component({
  selector: 'app-admin-roles',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  styleUrl: './admin-roles.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <div class="dv-pagehead">
          <h1 class="dv-h1 dv-h1--sm">Admin</h1>
          <dv-subnav />
          <button type="button" class="dv-btn dv-btn--primary dv-push" (click)="startCreate()">
            + New role
          </button>
        </div>

        @if (errorMessage()) {
          <div class="ar-banner ar-banner--error" role="alert">
            <span>{{ errorMessage() }}</span>
            <button
              type="button"
              class="ar-banner__close"
              aria-label="Dismiss"
              (click)="errorMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        @if (successMessage()) {
          <div class="ar-banner ar-banner--ok" role="status">
            <span>{{ successMessage() }}</span>
            <button
              type="button"
              class="ar-banner__close"
              aria-label="Dismiss"
              (click)="successMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        <!-- Create / Edit form -->
        @if (showForm()) {
          <div class="dv-card dv-card--pad dv-card--accent ar-form">
            <div class="dv-card__title">{{ editing() ? 'Edit role' : 'New role' }}</div>

            <div class="ar-form__row">
              <div>
                <label class="dv-field__label" for="ar-name">role name *</label>
                <input
                  id="ar-name"
                  type="text"
                  class="dv-input"
                  [(ngModel)]="formName"
                  placeholder="e.g. Document Manager"
                />
              </div>
            </div>

            <div class="ar-perms">
              <span class="dv-field__label">permissions</span>
              @if (permissions().length === 0) {
                <span class="dv-meta">No permissions available.</span>
              } @else {
                <div class="dv-well ar-perms__box">
                  @for (perm of permissions(); track perm.id) {
                    <label class="ar-check" [for]="'rperm-' + perm.id">
                      <input
                        class="dv-checkbox"
                        type="checkbox"
                        [id]="'rperm-' + perm.id"
                        [checked]="formPermissions.includes(perm.id)"
                        (change)="togglePermission(perm.id, $event)"
                      />
                      <span>{{ perm.name }}</span>
                    </label>
                  }
                </div>
              }
            </div>

            <div class="ar-form__actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--md"
                (click)="save()"
                [disabled]="saving() || !formName.trim()"
              >
                @if (saving()) {
                  <span class="dv-spinner"></span>
                }
                {{ editing() ? 'Save changes' : 'Create role' }}
              </button>
              <button type="button" class="dv-btn dv-btn--ghost dv-btn--md" (click)="cancelForm()">
                Cancel
              </button>
            </div>
          </div>
        }

        <!-- Roles -->
        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading roles…</div>
        } @else if (roles().length === 0) {
          <div class="dv-empty">No roles defined yet.</div>
        } @else {
          <div class="ar-grid">
            @for (role of roles(); track role.id) {
              <div class="dv-card ar-card">
                <div class="ar-card__head">
                  <span class="ar-card__name">{{ role.name }}</span>
                  <span class="dv-meta dv-push">
                    {{ role.permissions.length }} permission{{
                      role.permissions.length !== 1 ? 's' : ''
                    }}
                  </span>
                </div>

                <div class="ar-card__perms">
                  @if (role.permissions.length === 0) {
                    <span class="dv-meta">no permissions granted</span>
                  }
                  @for (pid of visiblePermissions(role); track pid) {
                    <span class="dv-chip dv-chip--outline-strong">{{ permissionName(pid) }}</span>
                  }
                  @if (hiddenPermissionCount(role) > 0) {
                    <span class="dv-chip dv-chip--well">+{{ hiddenPermissionCount(role) }} more</span>
                  }
                </div>

                <div class="ar-card__foot">
                  <button type="button" class="ar-action" (click)="startEdit(role)">edit</button>
                  <button
                    type="button"
                    class="ar-action ar-action--danger"
                    (click)="deleteRole(role)"
                  >
                    delete
                  </button>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class AdminRolesComponent implements OnInit {
  roles = signal<Role[]>([]);
  permissions = signal<Permission[]>([]);
  loading = signal(false);
  saving = signal(false);
  showForm = signal(false);
  editing = signal<Role | null>(null);
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
    this.securityService.getRoles().subscribe({
      next: (roles) => {
        this.roles.set(roles);
        this.loading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to load roles.');
        this.loading.set(false);
      },
    });
    this.securityService.getPermissions().subscribe({
      next: (perms) => this.permissions.set(perms),
    });
  }

  /** Codename of a granted permission, for the chip row on a role card. */
  permissionName(id: number): string {
    const perm = this.permissions().find((p) => p.id === id);
    return perm?.codename ?? `#${id}`;
  }

  /** First few granted permissions — a full list would swamp the card. */
  visiblePermissions(role: Role): number[] {
    return role.permissions.slice(0, ROLE_CHIP_LIMIT);
  }

  hiddenPermissionCount(role: Role): number {
    return Math.max(0, role.permissions.length - ROLE_CHIP_LIMIT);
  }

  startCreate(): void {
    this.editing.set(null);
    this.formName = '';
    this.formPermissions = [];
    this.showForm.set(true);
  }

  startEdit(role: Role): void {
    this.editing.set(role);
    this.formName = role.name;
    this.formPermissions = [...role.permissions];
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
    const data: Partial<Role> = {
      name: this.formName.trim(),
      permissions: this.formPermissions,
    };

    this.saving.set(true);
    this.errorMessage.set('');

    const editingRole = this.editing();
    const request = editingRole
      ? this.securityService.updateRole(editingRole.id, data)
      : this.securityService.createRole(data);

    request.subscribe({
      next: () => {
        this.successMessage.set(editingRole ? 'Role updated.' : 'Role created.');
        this.saving.set(false);
        this.cancelForm();
        this.load();
      },
      error: () => {
        this.errorMessage.set(editingRole ? 'Failed to update role.' : 'Failed to create role.');
        this.saving.set(false);
      },
    });
  }

  deleteRole(role: Role): void {
    if (!confirm(`Delete role "${role.name}"? This action cannot be undone.`)) return;
    this.securityService.deleteRole(role.id).subscribe({
      next: () => {
        this.successMessage.set(`Role "${role.name}" deleted.`);
        this.load();
      },
      error: () => {
        this.errorMessage.set('Failed to delete role.');
      },
    });
  }
}
