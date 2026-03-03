import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MlService } from '../../services/ml.service';
import { ClassifierStatus } from '../../models/ml.model';

@Component({
  selector: 'app-classifier-status',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './classifier-status.component.html',
})
export class ClassifierStatusComponent implements OnInit {
  status = signal<ClassifierStatus | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  training = signal(false);
  trainMessage = signal<string | null>(null);

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
