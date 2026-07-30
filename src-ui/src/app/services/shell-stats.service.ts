import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { DocumentService } from './document.service';

interface DedupStats {
  total_blobs: number;
  total_size_bytes: number;
  deduplicated_size_bytes: number;
  savings_bytes: number;
  savings_percent: number;
}

interface ProcessingTaskLite {
  status: string;
}

/**
 * Backs the command bar's status readout (`● ocr idle | 1,284 docs | 3.2 GB`).
 *
 * Each figure comes from an endpoint the shell already has access to. On-disk
 * size is staff-only (`/storage/dedup-stats/` requires IsAdminUser), so for
 * everyone else the segment is omitted rather than guessed at.
 */
@Injectable({ providedIn: 'root' })
export class ShellStatsService {
  private readonly http = inject(HttpClient);
  private readonly documents = inject(DocumentService);

  private readonly documentCountSignal = signal<number | null>(null);
  private readonly activeTasksSignal = signal<number | null>(null);
  private readonly diskBytesSignal = signal<number | null>(null);

  readonly documentCount = this.documentCountSignal.asReadonly();
  readonly activeTasks = this.activeTasksSignal.asReadonly();

  readonly ocrLabel = computed(() => {
    const active = this.activeTasksSignal();
    if (active === null) return 'ocr —';
    return active === 0 ? 'ocr idle' : `ocr ${active} running`;
  });

  readonly ocrBusy = computed(() => (this.activeTasksSignal() ?? 0) > 0);

  readonly documentsLabel = computed(() => {
    const count = this.documentCountSignal();
    return count === null ? null : `${count.toLocaleString()} docs`;
  });

  readonly storageLabel = computed(() => {
    const bytes = this.diskBytesSignal();
    return bytes === null ? null : formatBytes(bytes);
  });

  /** @param staff whether to attempt the admin-only storage figure. */
  refresh(staff: boolean): void {
    this.documents.getDocuments({ page_size: 1 }).subscribe({
      next: (page) => this.documentCountSignal.set(page.count),
      error: () => this.documentCountSignal.set(null),
    });

    this.http
      .get<ProcessingTaskLite[] | { results: ProcessingTaskLite[] }>(
        `${environment.apiUrl}/tasks/`,
      )
      .subscribe({
        next: (response) => {
          const tasks = Array.isArray(response) ? response : response.results;
          const active = (tasks ?? []).filter(
            (t) => t.status === 'pending' || t.status === 'started',
          ).length;
          this.activeTasksSignal.set(active);
        },
        error: () => this.activeTasksSignal.set(null),
      });

    if (!staff) {
      this.diskBytesSignal.set(null);
      return;
    }

    this.http
      .get<DedupStats>(`${environment.apiUrl}/storage/dedup-stats/`)
      .subscribe({
        next: (stats) =>
          this.diskBytesSignal.set(stats.deduplicated_size_bytes),
        error: () => this.diskBytesSignal.set(null),
      });
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}
