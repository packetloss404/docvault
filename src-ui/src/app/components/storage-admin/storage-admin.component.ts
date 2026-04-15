import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface DedupStats {
  total_blobs: number;
  total_size_bytes: number;
  deduplicated_size_bytes: number;
  savings_bytes: number;
  savings_percent: number;
}

interface IntegrityResult {
  total_checked: number;
  passed: number;
  failed: number;
  errors: Array<{ file: string; reason: string }>;
}

@Component({
  selector: 'app-storage-admin',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './storage-admin.component.html',
})
export class StorageAdminComponent implements OnInit {
  private readonly apiUrl = environment.apiUrl;

  dedupStats = signal<DedupStats | null>(null);
  dedupLoading = signal(false);

  integrityResult = signal<IntegrityResult | null>(null);
  integrityRunning = signal(false);

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadDedupStats();
  }

  loadDedupStats(): void {
    this.dedupLoading.set(true);
    this.http.get<DedupStats>(`${this.apiUrl}/storage/dedup-stats/`).subscribe({
      next: (stats) => {
        this.dedupStats.set(stats);
        this.dedupLoading.set(false);
      },
      error: () => this.dedupLoading.set(false),
    });
  }

  runIntegrityCheck(): void {
    this.integrityRunning.set(true);
    this.integrityResult.set(null);
    this.http.post<IntegrityResult>(`${this.apiUrl}/storage/verify-integrity/`, {}).subscribe({
      next: (result) => {
        this.integrityResult.set(result);
        this.integrityRunning.set(false);
      },
      error: () => this.integrityRunning.set(false),
    });
  }

  formatBytes(bytes: number): string {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
  }
}
