import { Injectable, inject, signal } from '@angular/core';
import { DocumentService } from './document.service';

/**
 * Single ingest path for every upload affordance: the command bar's `Upload ⇧U`
 * button, the dashboard drop zone, and the shell-wide "drop files anywhere".
 *
 * `completedTick` increments after each batch so screens can refresh their lists
 * without the shell needing to know what they show.
 */
@Injectable({ providedIn: 'root' })
export class UploadService {
  private readonly documents = inject(DocumentService);

  private readonly uploadingSignal = signal(false);
  private readonly messageSignal = signal('');
  private readonly errorSignal = signal(false);
  private readonly tickSignal = signal(0);
  private readonly dragActiveSignal = signal(false);

  readonly uploading = this.uploadingSignal.asReadonly();
  readonly message = this.messageSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();
  readonly completedTick = this.tickSignal.asReadonly();
  readonly dragActive = this.dragActiveSignal.asReadonly();

  setDragActive(active: boolean): void {
    this.dragActiveSignal.set(active);
  }

  processingCompleted(): void {
    this.tickSignal.update((value) => value + 1);
  }

  /** Opens a file picker and uploads whatever is chosen. */
  pick(): void {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.pdf,.png,.jpg,.jpeg,.tif,.tiff,.doc,.docx,.xls,.xlsx,.odt,.eml,.msg,.txt';
    input.addEventListener('change', () => {
      if (input.files?.length) this.upload(input.files);
    });
    input.click();
  }

  upload(files: FileList | File[]): void {
    const list = Array.from(files);
    if (!list.length) return;

    this.uploadingSignal.set(true);
    this.messageSignal.set('');
    this.errorSignal.set(false);

    let completed = 0;
    let failed = 0;
    const done = () => {
      if (completed + failed < list.length) return;
      this.uploadingSignal.set(false);
      this.errorSignal.set(failed > 0);
      this.messageSignal.set(
        failed === 0
          ? `Uploaded ${completed} file${completed === 1 ? '' : 's'}.`
          : `Uploaded ${completed} of ${list.length}; ${failed} failed.`,
      );
      this.tickSignal.update((n) => n + 1);
    };

    for (const file of list) {
      const form = new FormData();
      form.append('document', file);
      form.append('title', file.name);
      this.documents
        .uploadDocument(form)
        .subscribe({
          next: () => {
            completed++;
            done();
          },
          error: () => {
            failed++;
            done();
          },
        });
    }
  }

  clearMessage(): void {
    this.messageSignal.set('');
  }
}
