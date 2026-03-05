import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BarcodeService } from '../../services/barcode.service';
import { AsnAssignment, BarcodeConfig } from '../../models/barcode.model';

@Component({
  selector: 'app-barcode-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './barcode-config.component.html',
})
export class BarcodeConfigComponent implements OnInit {
  config = signal<BarcodeConfig | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  nextAsn = signal<number | null>(null);
  asnLoading = signal(false);
  asnError = signal<string | null>(null);

  documentIdsInput = signal('');
  assigning = signal(false);
  assignError = signal<string | null>(null);
  assignResults = signal<AsnAssignment[]>([]);
  assignCount = signal<number | null>(null);

  constructor(private barcodeService: BarcodeService) {}

  ngOnInit(): void {
    this.loadConfig();
    this.loadNextAsn();
  }

  loadConfig(): void {
    this.loading.set(true);
    this.error.set(null);

    this.barcodeService.getBarcodeConfig().subscribe({
      next: (config) => {
        this.config.set(config);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load barcode configuration');
        this.loading.set(false);
      },
    });
  }

  loadNextAsn(): void {
    this.asnLoading.set(true);
    this.asnError.set(null);

    this.barcodeService.getNextAsn().subscribe({
      next: (resp) => {
        this.nextAsn.set(resp.next_asn);
        this.asnLoading.set(false);
      },
      error: () => {
        this.asnError.set('Failed to load next ASN');
        this.asnLoading.set(false);
      },
    });
  }

  tagMappingEntries(): Array<{ pattern: string; tag: string }> {
    const cfg = this.config();
    if (!cfg || !cfg.tag_mapping) {
      return [];
    }
    return Object.entries(cfg.tag_mapping).map(([pattern, tag]) => ({
      pattern,
      tag,
    }));
  }

  bulkAssign(): void {
    const raw = this.documentIdsInput().trim();
    if (!raw) {
      this.assignError.set('Please enter at least one document ID');
      return;
    }

    const ids = raw
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      .map((s) => parseInt(s, 10));

    if (ids.some((id) => isNaN(id))) {
      this.assignError.set(
        'Invalid input: all values must be numeric document IDs',
      );
      return;
    }

    this.assigning.set(true);
    this.assignError.set(null);
    this.assignResults.set([]);
    this.assignCount.set(null);

    this.barcodeService.bulkAssignAsn(ids).subscribe({
      next: (result) => {
        this.assignResults.set(result.assigned);
        this.assignCount.set(result.count);
        this.assigning.set(false);
        // Refresh next ASN after bulk assignment
        this.loadNextAsn();
      },
      error: () => {
        this.assignError.set('Failed to assign ASNs');
        this.assigning.set(false);
      },
    });
  }
}
