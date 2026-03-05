import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SecurityService, AuditLogQueryParams } from '../../services/security.service';
import { AuditLogEntry } from '../../models/security.model';

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audit-log.component.html',
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

  getActionBadgeClass(action: string): string {
    switch (action) {
      case 'create':
      case 'upload':
        return 'bg-success';
      case 'delete':
        return 'bg-danger';
      case 'update':
        return 'bg-primary';
      case 'login':
      case 'logout':
        return 'bg-info';
      case 'download':
      case 'view':
        return 'bg-secondary';
      case 'sign':
      case 'verify':
        return 'bg-warning text-dark';
      default:
        return 'bg-secondary';
    }
  }
}
