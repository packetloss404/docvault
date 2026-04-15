import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { User, Group } from '../../models/security.model';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container-fluid py-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0"><i class="bi bi-people me-2"></i>User Management</h2>
        <button class="btn btn-primary" (click)="startCreate()">
          <i class="bi bi-plus-lg me-1"></i> New User
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
            <h5 class="mb-0">{{ editing() ? 'Edit User' : 'Create User' }}</h5>
          </div>
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Username <span class="text-danger">*</span></label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formUsername"
                  placeholder="username"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label">Email</label>
                <input
                  type="email"
                  class="form-control"
                  [(ngModel)]="formEmail"
                  placeholder="user@example.com"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label">First Name</label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formFirstName"
                  placeholder="First name"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label">Last Name</label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formLastName"
                  placeholder="Last name"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label">Password {{ editing() ? '(leave blank to keep current)' : '' }}</label>
                <input
                  type="password"
                  class="form-control"
                  [(ngModel)]="formPassword"
                  placeholder="{{ editing() ? 'New password (optional)' : 'Password' }}"
                />
              </div>
              <div class="col-md-3 d-flex align-items-end">
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="isActive"
                    [(ngModel)]="formIsActive"
                  />
                  <label class="form-check-label" for="isActive">Active</label>
                </div>
              </div>
              <div class="col-md-3 d-flex align-items-end">
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="isStaff"
                    [(ngModel)]="formIsStaff"
                  />
                  <label class="form-check-label" for="isStaff">Staff / Admin</label>
                </div>
              </div>
              <div class="col-12">
                <label class="form-label">Groups</label>
                <div class="d-flex flex-wrap gap-2">
                  @for (group of groups(); track group.id) {
                    <div class="form-check">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        [id]="'group-' + group.id"
                        [checked]="formGroups.includes(group.id)"
                        (change)="toggleGroup(group.id, $event)"
                      />
                      <label class="form-check-label" [for]="'group-' + group.id">
                        {{ group.name }}
                      </label>
                    </div>
                  }
                  @if (groups().length === 0) {
                    <span class="text-muted small">No groups defined yet.</span>
                  }
                </div>
              </div>
            </div>
            <div class="mt-3 d-flex gap-2">
              <button
                class="btn btn-primary"
                (click)="save()"
                [disabled]="saving() || !formUsername.trim()"
              >
                @if (saving()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                }
                {{ editing() ? 'Save Changes' : 'Create User' }}
              </button>
              <button class="btn btn-outline-secondary" (click)="cancelForm()">Cancel</button>
            </div>
          </div>
        </div>
      }

      <!-- Users Table -->
      <div class="card">
        <div class="card-header">
          <h5 class="mb-0">Users</h5>
        </div>
        <div class="card-body p-0">
          @if (loading()) {
            <div class="text-center py-5">
              <div class="spinner-border text-primary"></div>
              <p class="mt-2 text-muted">Loading users…</p>
            </div>
          } @else if (users().length === 0) {
            <div class="text-center py-5 text-muted">
              <i class="bi bi-people fs-1 d-block mb-2"></i>
              No users found.
            </div>
          } @else {
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                  <tr>
                    <th>Username</th>
                    <th>Full Name</th>
                    <th>Email</th>
                    <th>Groups</th>
                    <th>Status</th>
                    <th class="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (user of users(); track user.id) {
                    <tr>
                      <td>
                        <strong>{{ user.username }}</strong>
                        @if (user.is_staff) {
                          <span class="badge bg-warning text-dark ms-1">Staff</span>
                        }
                      </td>
                      <td>{{ user.first_name }} {{ user.last_name }}</td>
                      <td>{{ user.email || '—' }}</td>
                      <td>
                        @for (gid of user.groups; track gid) {
                          <span class="badge bg-secondary me-1">{{ groupName(gid) }}</span>
                        }
                        @if (user.groups.length === 0) {
                          <span class="text-muted small">—</span>
                        }
                      </td>
                      <td>
                        @if (user.is_active) {
                          <span class="badge bg-success">Active</span>
                        } @else {
                          <span class="badge bg-secondary">Inactive</span>
                        }
                      </td>
                      <td class="text-end">
                        <button
                          class="btn btn-sm btn-outline-primary me-1"
                          (click)="startEdit(user)"
                        >
                          <i class="bi bi-pencil"></i>
                        </button>
                        <button
                          class="btn btn-sm btn-outline-danger"
                          (click)="deleteUser(user)"
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
