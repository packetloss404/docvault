import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { User, Group } from '../../models/security.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <div class="dv-pagehead">
          <h1 class="dv-h1 dv-h1--sm">Admin</h1>
          <dv-subnav />
          <button type="button" class="dv-btn dv-btn--primary dv-push" (click)="startCreate()">
            + Invite user
          </button>
        </div>

        @if (errorMessage()) {
          <div class="au-banner au-banner--error" role="alert">
            <span>{{ errorMessage() }}</span>
            <button
              type="button"
              class="au-banner__close"
              aria-label="Dismiss"
              (click)="errorMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        @if (successMessage()) {
          <div class="au-banner au-banner--ok" role="status">
            <span>{{ successMessage() }}</span>
            <button
              type="button"
              class="au-banner__close"
              aria-label="Dismiss"
              (click)="successMessage.set('')"
            >
              ✕
            </button>
          </div>
        }

        <!-- Create / Edit form -->
        @if (showForm()) {
          <div class="dv-card dv-card--pad dv-card--accent au-form">
            <div class="dv-card__title">{{ editing() ? 'Edit user' : 'Invite user' }}</div>

            <div class="au-form__grid">
              <div>
                <label class="dv-field__label" for="au-username">username *</label>
                <input
                  id="au-username"
                  type="text"
                  class="dv-input"
                  [(ngModel)]="formUsername"
                  placeholder="username"
                />
              </div>
              <div>
                <label class="dv-field__label" for="au-email">email</label>
                <input
                  id="au-email"
                  type="email"
                  class="dv-input"
                  [(ngModel)]="formEmail"
                  placeholder="user@example.com"
                />
              </div>
              <div>
                <label class="dv-field__label" for="au-first">first name</label>
                <input
                  id="au-first"
                  type="text"
                  class="dv-input"
                  [(ngModel)]="formFirstName"
                  placeholder="First name"
                />
              </div>
              <div>
                <label class="dv-field__label" for="au-last">last name</label>
                <input
                  id="au-last"
                  type="text"
                  class="dv-input"
                  [(ngModel)]="formLastName"
                  placeholder="Last name"
                />
              </div>
              <div>
                <label class="dv-field__label" for="au-password">
                  password {{ editing() ? '(blank keeps current)' : '' }}
                </label>
                <input
                  id="au-password"
                  type="password"
                  class="dv-input dv-input--mono"
                  [(ngModel)]="formPassword"
                  [placeholder]="editing() ? 'New password (optional)' : 'Password'"
                />
              </div>
              <div>
                <span class="dv-field__label">flags</span>
                <div class="au-checks">
                  <label class="au-check" for="isActive">
                    <input
                      class="dv-checkbox"
                      type="checkbox"
                      id="isActive"
                      [(ngModel)]="formIsActive"
                    />
                    active
                  </label>
                  <label class="au-check" for="isStaff">
                    <input
                      class="dv-checkbox"
                      type="checkbox"
                      id="isStaff"
                      [(ngModel)]="formIsStaff"
                    />
                    staff / admin
                  </label>
                </div>
              </div>
              <div class="au-form__wide">
                <span class="dv-field__label">groups</span>
                <div class="au-checks">
                  @for (group of groups(); track group.id) {
                    <label class="au-check" [for]="'group-' + group.id">
                      <input
                        class="dv-checkbox"
                        type="checkbox"
                        [id]="'group-' + group.id"
                        [checked]="formGroups.includes(group.id)"
                        (change)="toggleGroup(group.id, $event)"
                      />
                      {{ group.name }}
                    </label>
                  }
                  @if (groups().length === 0) {
                    <span class="dv-meta">No groups defined yet.</span>
                  }
                </div>
              </div>
            </div>

            <div class="au-form__actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--md"
                (click)="save()"
                [disabled]="saving() || !formUsername.trim()"
              >
                @if (saving()) {
                  <span class="dv-spinner"></span>
                }
                {{ editing() ? 'Save changes' : 'Create user' }}
              </button>
              <button type="button" class="dv-btn dv-btn--ghost dv-btn--md" (click)="cancelForm()">
                Cancel
              </button>
            </div>
          </div>
        }

        <!-- Users table -->
        <div class="au-table">
          @if (loading()) {
            <div class="dv-empty"><span class="dv-spinner"></span> Loading users…</div>
          } @else if (users().length === 0) {
            <div class="dv-empty">No users found.</div>
          } @else {
            <div
              class="dv-thead dv-grid"
              style="--dv-cols: 36px 1fr 110px minmax(0, 1fr) 90px 100px"
            >
              <span></span><span>user</span><span>role</span><span>groups</span>
              <span>status</span><span></span>
            </div>
            @for (user of users(); track user.id) {
              <div
                class="dv-row dv-row--static dv-grid"
                style="--dv-cols: 36px 1fr 110px minmax(0, 1fr) 90px 100px"
              >
                <span class="dv-avatar dv-avatar--md">{{ initials(user) }}</span>
                <div class="dv-clip">
                  <div class="au-user__name">
                    {{ fullName(user) }}
                  </div>
                  <div class="dv-meta dv-clip">{{ user.email || user.username }}</div>
                </div>
                <span>
                  <span class="dv-chip" [class.dv-chip--accent]="user.is_staff">
                    {{ user.is_staff ? 'staff' : 'user' }}
                  </span>
                </span>
                <span class="au-groups">
                  @for (gid of user.groups; track gid) {
                    <span class="dv-chip dv-chip--outline">{{ groupName(gid) }}</span>
                  }
                  @if (user.groups.length === 0) {
                    <span class="dv-meta">—</span>
                  }
                </span>
                <span class="dv-meta" [class.dv-ok]="user.is_active">
                  {{ user.is_active ? '✓ active' : 'inactive' }}
                </span>
                <span class="au-actions">
                  <button type="button" class="au-action" (click)="startEdit(user)">edit</button>
                  <button
                    type="button"
                    class="au-action au-action--danger"
                    (click)="deleteUser(user)"
                  >
                    del
                  </button>
                </span>
              </div>
            }
          }
        </div>
      </div>
    </div>
  `,
  styleUrl: './admin-users.component.scss',
})
export class AdminUsersComponent implements OnInit {
  users = signal<User[]>([]);
  groups = signal<Group[]>([]);
  loading = signal(false);
  saving = signal(false);
  showForm = signal(false);
  editing = signal<User | null>(null);
  errorMessage = signal('');
  successMessage = signal('');

  // Form fields
  formUsername = '';
  formEmail = '';
  formFirstName = '';
  formLastName = '';
  formPassword = '';
  formIsActive = true;
  formIsStaff = false;
  formGroups: number[] = [];

  constructor(private securityService: SecurityService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.securityService.getUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.loading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to load users.');
        this.loading.set(false);
      },
    });
    this.securityService.getGroups().subscribe({
      next: (groups) => this.groups.set(groups),
    });
  }

  groupName(id: number): string {
    return this.groups().find((g) => g.id === id)?.name ?? String(id);
  }

  /** "Ada Lovelace" when the names are set, otherwise the username. */
  fullName(user: User): string {
    const name = `${user.first_name} ${user.last_name}`.trim();
    return name || user.username;
  }

  /** Two-letter avatar label, mirroring the rail avatar chip. */
  initials(user: User): string {
    const first = user.first_name?.trim();
    const last = user.last_name?.trim();
    if (first && last) return (first[0] + last[0]).toLowerCase();
    return user.username.slice(0, 2).toLowerCase();
  }

  startCreate(): void {
    this.editing.set(null);
    this.formUsername = '';
    this.formEmail = '';
    this.formFirstName = '';
    this.formLastName = '';
    this.formPassword = '';
    this.formIsActive = true;
    this.formIsStaff = false;
    this.formGroups = [];
    this.showForm.set(true);
  }

  startEdit(user: User): void {
    this.editing.set(user);
    this.formUsername = user.username;
    this.formEmail = user.email;
    this.formFirstName = user.first_name;
    this.formLastName = user.last_name;
    this.formPassword = '';
    this.formIsActive = user.is_active;
    this.formIsStaff = user.is_staff;
    this.formGroups = [...user.groups];
    this.showForm.set(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelForm(): void {
    this.showForm.set(false);
    this.editing.set(null);
  }

  toggleGroup(id: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.formGroups = [...this.formGroups, id];
    } else {
      this.formGroups = this.formGroups.filter((g) => g !== id);
    }
  }

  save(): void {
    const data: Partial<User> & { password?: string } = {
      username: this.formUsername.trim(),
      email: this.formEmail.trim(),
      first_name: this.formFirstName.trim(),
      last_name: this.formLastName.trim(),
      is_active: this.formIsActive,
      is_staff: this.formIsStaff,
      groups: this.formGroups,
    };
    if (this.formPassword) {
      data['password'] = this.formPassword;
    }

    this.saving.set(true);
    this.errorMessage.set('');

    const editingUser = this.editing();
    const request = editingUser
      ? this.securityService.updateUser(editingUser.id, data)
      : this.securityService.createUser(data);

    request.subscribe({
      next: () => {
        this.successMessage.set(editingUser ? 'User updated.' : 'User created.');
        this.saving.set(false);
        this.cancelForm();
        this.load();
      },
      error: () => {
        this.errorMessage.set(editingUser ? 'Failed to update user.' : 'Failed to create user.');
        this.saving.set(false);
      },
    });
  }

  deleteUser(user: User): void {
    if (!confirm(`Delete user "${user.username}"? This action cannot be undone.`)) return;
    this.securityService.deleteUser(user.id).subscribe({
      next: () => {
        this.successMessage.set(`User "${user.username}" deleted.`);
        this.load();
      },
      error: () => {
        this.errorMessage.set('Failed to delete user.');
      },
    });
  }
}
