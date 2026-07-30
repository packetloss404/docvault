import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService } from '../../services/security.service';
import { Permission } from '../../models/security.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-permissions-browser',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  styleUrl: './permissions-browser.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <div class="dv-pagehead">
          <h1 class="dv-h1 dv-h1--sm">Admin</h1>
          <dv-subnav />
          <span class="dv-meta dv-push">
            {{ filteredPermissions().length }} / {{ permissions().length }} permissions
          </span>
        </div>

        <!-- Filter -->
        <div class="pb-filter">
          <input
            type="text"
            class="dv-input"
            placeholder="Filter by codename or name…"
            aria-label="Filter permissions"
            [(ngModel)]="searchQuery"
            (ngModelChange)="onSearchChange($event)"
          />
          @if (searchQuery) {
            <button type="button" class="dv-btn dv-btn--ghost dv-btn--sm" (click)="clearSearch()">
              ✕ clear
            </button>
          }
        </div>

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading permissions…</div>
        }

        @if (error()) {
          <div class="pb-error" role="alert">{{ error() }}</div>
        }

        @if (!loading() && !error()) {
          <div class="dv-thead dv-grid" style="--dv-cols: minmax(0, 1fr) minmax(0, 1fr) 120px 70px">
            <span>codename</span><span>display name</span><span>content type</span>
            <span class="dv-num">id</span>
          </div>

          @for (perm of filteredPermissions(); track perm.id) {
            <div
              class="dv-row dv-row--static dv-row--tight dv-grid"
              style="--dv-cols: minmax(0, 1fr) minmax(0, 1fr) 120px 70px"
            >
              <span class="dv-mono dv-accent dv-clip">{{ perm.codename }}</span>
              <span class="dv-clip">{{ perm.name }}</span>
              <span><span class="dv-chip dv-chip--well">ct {{ perm.content_type }}</span></span>
              <span class="dv-meta dv-num">{{ perm.id }}</span>
            </div>
          } @empty {
            <div class="dv-empty">
              @if (searchQuery) {
                No permissions match “{{ searchQuery }}”.
              } @else {
                No permissions defined.
              }
            </div>
          }

          @if (filteredPermissions().length > 0) {
            <div class="dv-meta pb-foot">
              showing {{ filteredPermissions().length }} permission{{
                filteredPermissions().length !== 1 ? 's' : ''
              }}@if (searchQuery) {
                <span> matching “{{ searchQuery }}”</span>
              }
            </div>
          }
        }
      </div>
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
