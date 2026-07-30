import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService, AuditLogQueryParams } from '../../services/security.service';
import { AuditLogEntry } from '../../models/security.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule, SubnavComponent],
  templateUrl: './audit-log.component.html',
  styleUrl: './audit-log.component.scss',
})
export class AuditLogComponent implements OnInit {
  entries = signal<AuditLogEntry[]>([]);
  loading = signal(false);
  totalCount = signal(0);
  currentPage = signal(1);
  pageSize = 25;

  // Filters
  filterUser = '';
  filterAction = '';
  filterFromDate = '';
  filterToDate = '';

  exportLoading = signal(false);
  errorMessage = signal('');

  readonly actionTypes = [
    'create',
    'update',
    'delete',
    'login',
    'logout',
    'download',
    'view',
    'share',
    'sign',
    'verify',
    'upload',
    'restore',
  ];

  constructor(private securityService: SecurityService) {}

  ngOnInit(): void {
    this.loadAuditLog();
  }

  loadAuditLog(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    const params: AuditLogQueryParams = {
      page: this.currentPage(),
      page_size: this.pageSize,
    };

    if (this.filterAction) {
      params.action = this.filterAction;
    }
    if (this.filterFromDate) {
      params.from_date = this.filterFromDate;
    }
    if (this.filterToDate) {
      params.to_date = this.filterToDate;
    }

    this.securityService.getAuditLog(params).subscribe({
      next: (response) => {
        this.entries.set(response.results);
        this.totalCount.set(response.count);
        this.loading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to load audit log. You may not have admin permissions.');
        this.loading.set(false);
      },
    });
  }

  /**
   * The API filters by action and date range; the free-text box narrows the
   * page that is already loaded (the endpoint takes a numeric user id only,
   * so there is nothing to send it).
   */
  displayedEntries(): AuditLogEntry[] {
    const query = this.filterUser.toLowerCase().trim();
    if (!query) return this.entries();
    return this.entries().filter((e) =>
      [e.username, e.action, e.model_type, e.detail, e.ip_address]
        .filter((v): v is string => !!v)
        .some((v) => v.toLowerCase().includes(query)),
    );
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadAuditLog();
  }

  clearFilters(): void {
    this.filterUser = '';
    this.filterAction = '';
    this.filterFromDate = '';
    this.filterToDate = '';
    this.currentPage.set(1);
    this.loadAuditLog();
  }

  goToPage(page: number): void {
    this.currentPage.set(page);
    this.loadAuditLog();
  }

  get totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize);
  }

  get pageNumbers(): number[] {
    const total = this.totalPages;
    const current = this.currentPage();
    const pages: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }

  exportLog(format: 'csv' | 'json'): void {
    this.exportLoading.set(true);

    const params: AuditLogQueryParams = {};
    if (this.filterAction) params.action = this.filterAction;
    if (this.filterFromDate) params.from_date = this.filterFromDate;
    if (this.filterToDate) params.to_date = this.filterToDate;

    this.securityService.exportAuditLog(format, params).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-log.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.exportLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Failed to export audit log.');
        this.exportLoading.set(false);
      },
    });
  }

  formatTimestamp(ts: string): string {
    return new Date(ts).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  /**
   * Colour the action word by class: authentication and integrity read ok,
   * reads and writes read accent, mutations warn, destructive danger.
   */
  getActionBadgeClass(action: string): string {
    switch (action) {
      case 'login':
      case 'logout':
      case 'verify':
        return 'dv-ok';
      case 'create':
      case 'upload':
      case 'download':
      case 'view':
      case 'restore':
        return 'dv-accent';
      case 'update':
      case 'share':
      case 'sign':
        return 'dv-warn';
      case 'delete':
        return 'dv-danger';
      default:
        return 'dv-muted';
    }
  }
}
