import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { Permission } from '../../models/security.model';

@Component({
  selector: 'app-permissions-browser',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container-fluid">
      <div class="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h2 class="mb-1">
            <i class="bi bi-key me-2 text-primary"></i>Permissions Browser
          </h2>
          <p class="text-muted mb-0 small">
            All system permissions available for assignment to groups and roles.
          </p>
        </div>
        <span class="badge bg-secondary fs-6">
          {{ filteredPermissions().length }} of {{ permissions().length }}
        </span>
      </div>

      <!-- Search -->
      <div class="card mb-4 shadow-sm">
        <div class="card-body py-3">
          <div class="input-group">
            <span class="input-group-text">
              <i class="bi bi-search"></i>
            </span>
            <input
              type="text"
              class="form-control"
              placeholder="Filter by codename or name..."
              [(ngModel)]="searchQuery"
              (ngModelChange)="onSearchChange($event)"
            />
            @if (searchQuery) {
              <button class="btn btn-outline-secondary" type="button" (click)="clearSearch()">
                <i class="bi bi-x-lg"></i>
              </button>
            }
          </div>
        </div>
      </div>

      <!-- Loading -->
      @if (loading()) {
        <div class="text-center py-5">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="text-muted mt-2">Loading permissions...</p>
        </div>
      }

      <!-- Error -->
      @if (error()) {
        <div class="alert alert-danger d-flex align-items-center" role="alert">
          <i class="bi bi-exclamation-triangle-fill me-2"></i>
          <div>{{ error() }}</div>
        </div>
      }

      <!-- Table -->
      @if (!loading() && !error()) {
        <div class="card shadow-sm">
          <div class="table-responsive">
            <table class="table table-hover table-striped mb-0 align-middle">
              <thead class="table-dark">
                <tr>
                  <th scope="col" style="width: 60px;">#</th>
                  <th scope="col">Codename</th>
                  <th scope="col">Display Name</th>
                  <th scope="col" style="width: 130px;" class="text-center">Content Type ID</th>
                </tr>
              </thead>
              <tbody>
                @if (filteredPermissions().length === 0) {
                  <tr>
                    <td colspan="4" class="text-center py-4 text-muted">
                      <i class="bi bi-search me-2"></i>
                      No permissions match <strong>{{ searchQuery }}</strong>.
                    </td>
                  </tr>
                }
                @for (perm of filteredPermissions(); track perm.id) {
                  <tr>
                    <td class="text-muted small">{{ perm.id }}</td>
                    <td>
                      <code class="text-primary">{{ perm.codename }}</code>
                    </td>
                    <td>{{ perm.name }}</td>
                    <td class="text-center">
                      <span class="badge bg-light text-dark border">{{ perm.content_type }}</span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          @if (filteredPermissions().length > 0) {
            <div class="card-footer text-muted small">
              Showing {{ filteredPermissions().length }} permission{{ filteredPermissions().length !== 1 ? 's' : '' }}
              @if (searchQuery) {
                &nbsp;matching "<strong>{{ searchQuery }}</strong>"
              }
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class PermissionsBrowserComponent implements OnInit {
  permissions = signal<Permission[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  searchQuery = '';

  filteredPermissions = computed(() => {
    const query = this._searchSignal();
    if (!query) return this.permissions();
    const lower = query.toLowerCase();
    return this.permissions().filter(
      (p) =>
        p.codename.toLowerCase().includes(lower) ||
        p.name.toLowerCase().includes(lower),
    );
  });

  private _searchSignal = signal('');

  constructor(private securityService: SecurityService) {}

  ngOnInit(): void {
    this.securityService.getPermissions().subscribe({
      next: (perms) => {
        this.permissions.set(perms);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(
          err?.error?.detail ?? 'Failed to load permissions. Please try again.',
        );
        this.loading.set(false);
      },
    });
  }

  onSearchChange(value: string): void {
    this._searchSignal.set(value);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this._searchSignal.set('');
  }
}
