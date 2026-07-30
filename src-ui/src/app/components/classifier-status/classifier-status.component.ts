import { Component, OnInit, computed, signal } from '@angular/core';
import { MlService } from '../../services/ml.service';
import { ClassifierStatus } from '../../models/ml.model';
import { SubnavComponent } from '../subnav/subnav.component';

/** One row of the sub-classifier readout. */
export interface SubClassifierRow {
  key: string;
  label: string;
  trained: boolean;
  hash: string | undefined;
}

@Component({
  selector: 'app-classifier-status',
  standalone: true,
  imports: [SubnavComponent],
  templateUrl: './classifier-status.component.html',
  styleUrl: './classifier-status.component.scss',
})
export class ClassifierStatusComponent implements OnInit {
  status = signal<ClassifierStatus | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  training = signal(false);
  trainMessage = signal<string | null>(null);

  /** The four per-target classifiers the backend reports on. */
  readonly subClassifiers = computed<SubClassifierRow[]>(() => {
    const s = this.status();
    if (!s) return [];
    return [
      { key: 'tags', label: 'Tags', trained: s.tags_trained, hash: s.tags_data_hash },
      {
        key: 'correspondent',
        label: 'Correspondent',
        trained: s.correspondent_trained,
        hash: s.correspondent_data_hash,
      },
      {
        key: 'document_type',
        label: 'Document type',
        trained: s.document_type_trained,
        hash: s.document_type_data_hash,
      },
      {
        key: 'storage_path',
        label: 'Storage path',
        trained: s.storage_path_trained,
        hash: s.storage_path_data_hash,
      },
    ];
  });

  readonly trainedCount = computed(
    () => this.subClassifiers().filter((s) => s.trained).length,
  );

  constructor(private mlService: MlService) {}

  ngOnInit(): void {
    this.loadStatus();
  }

  loadStatus(): void {
    this.loading.set(true);
    this.error.set(null);

    this.mlService.getClassifierStatus().subscribe({
      next: (status) => {
        this.status.set(status);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load classifier status');
        this.loading.set(false);
      },
    });
  }

  triggerTraining(): void {
    this.training.set(true);
    this.trainMessage.set(null);

    this.mlService.triggerTraining().subscribe({
      next: (resp) => {
        this.trainMessage.set(
          `Training started (task: ${resp.task_id})`,
        );
        this.training.set(false);
      },
      error: () => {
        this.trainMessage.set('Failed to start training');
        this.training.set(false);
      },
    });
  }

  truncateHash(hash: string | undefined): string {
    if (!hash) return '--';
    return hash.length > 12 ? hash.substring(0, 12) + '...' : hash;
  }
}
