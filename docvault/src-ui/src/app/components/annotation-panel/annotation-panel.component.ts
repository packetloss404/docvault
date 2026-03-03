import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AnnotationService } from '../../services/annotation.service';
import { Annotation } from '../../models/annotation.model';

@Component({
  selector: 'app-annotation-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card h-100">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span>
          <i class="bi bi-chat-left-text me-1"></i>
          Annotations
          @if (annotations().length > 0) {
            <span class="badge bg-primary ms-1">{{ annotations().length }}</span>
          }
        </span>
        @if (currentPage) {
          <span class="badge bg-secondary">Page {{ currentPage }}</span>
        }
      </div>

      <div class="card-body overflow-auto p-0" style="max-height: 600px;">
        @if (loading()) {
          <div class="d-flex justify-content-center py-4">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
        } @else if (annotations().length === 0) {
          <div class="text-center text-muted py-4">
            <i class="bi bi-chat-left fs-3"></i>
            <p class="small mt-1 mb-0">No annotations on this page.</p>
          </div>
        } @else {
          @for (annotation of annotations(); track annotation.id) {
            <div
              class="border-bottom p-3 annotation-item"
              [class.bg-light]="selectedAnnotationId() === annotation.id"
              style="cursor: pointer;"
              (click)="onAnnotationClick(annotation)"
            >
              <!-- Header -->
              <div class="d-flex justify-content-between align-items-start mb-1">
                <div class="d-flex align-items-center gap-1">
                  <i class="bi" [ngClass]="getTypeIcon(annotation.annotation_type)"></i>
                  <span class="fw-semibold small">{{ annotation.author_name }}</span>
                  @if (annotation.is_private) {
                    <span class="badge bg-warning text-dark" style="font-size: 0.65em;">Private</span>
                  }
                </div>
                <div class="d-flex align-items-center gap-1">
                  <span
                    class="d-inline-block rounded-circle border"
                    [style.background]="annotation.color"
                    [style.opacity]="annotation.opacity"
                    style="width: 12px; height: 12px;"
                  ></span>
                  <button
                    class="btn btn-sm p-0 text-danger"
                    title="Delete annotation"
                    (click)="deleteAnnotation(annotation, $event)"
                  >
                    <i class="bi bi-trash" style="font-size: 0.8em;"></i>
                  </button>
                </div>
              </div>

              <!-- Timestamp -->
              <div class="text-muted" style="font-size: 0.75em;">
                {{ formatDate(annotation.created_at) }}
              </div>

              <!-- Content preview -->
              @if (annotation.content) {
                <p class="small mb-1 mt-1 text-truncate">{{ annotation.content }}</p>
              }

              <!-- Reply count / expand toggle -->
              @if (annotation.reply_count > 0) {
                <button
                  class="btn btn-sm btn-link p-0 text-decoration-none small"
                  (click)="toggleReplies(annotation, $event)"
                >
                  <i class="bi" [ngClass]="expandedAnnotation() === annotation.id ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                  {{ annotation.reply_count }} {{ annotation.reply_count === 1 ? 'reply' : 'replies' }}
                </button>
              }

              <!-- Expanded replies -->
              @if (expandedAnnotation() === annotation.id) {
                <div class="mt-2 ps-3 border-start">
                  @for (reply of annotation.replies; track reply.id) {
                    <div class="mb-2">
                      <div class="d-flex justify-content-between">
                        <span class="fw-semibold" style="font-size: 0.8em;">{{ reply.author_name }}</span>
                        <span class="text-muted" style="font-size: 0.7em;">{{ formatDate(reply.created_at) }}</span>
                      </div>
                      <p class="small mb-0">{{ reply.text }}</p>
                    </div>
                  }
                </div>
              }

              <!-- Add reply input -->
              @if (expandedAnnotation() === annotation.id || annotation.reply_count === 0) {
                <div class="mt-2">
                  <div class="input-group input-group-sm">
                    <input
                      type="text"
                      class="form-control"
                      placeholder="Add a reply..."
                      [ngModel]="replyTexts()[annotation.id] || ''"
                      (ngModelChange)="setReplyText(annotation.id, $event)"
                      (keyup.enter)="submitReply(annotation)"
                      (click)="$event.stopPropagation()"
                    />
                    <button
                      class="btn btn-outline-primary"
                      type="button"
                      [disabled]="!replyTexts()[annotation.id]"
                      (click)="submitReply(annotation); $event.stopPropagation()"
                    >
                      <i class="bi bi-send"></i>
                    </button>
                  </div>
                </div>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class AnnotationPanelComponent implements OnChanges {
  @Input() documentId = 0;
  @Input() currentPage = 1;
  @Input() authorFilter = '';

  @Output() annotationSelected = new EventEmitter<Annotation>();

  annotations = signal<Annotation[]>([]);
  loading = signal(false);
  selectedAnnotationId = signal<number | null>(null);
  expandedAnnotation = signal<number | null>(null);
  replyTexts = signal<Record<number, string>>({});

  constructor(private annotationService: AnnotationService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['documentId'] || changes['currentPage'] || changes['authorFilter']) {
      this.loadAnnotations();
    }
  }

  loadAnnotations(): void {
    if (!this.documentId) return;

    this.loading.set(true);
    const params: Record<string, string> = {};
    if (this.currentPage) {
      params['page'] = String(this.currentPage);
    }
    if (this.authorFilter) {
      params['author'] = this.authorFilter;
    }

    this.annotationService
      .getAnnotations(this.documentId, params)
      .subscribe({
        next: (data) => {
          this.annotations.set(data);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
        },
      });
  }

  onAnnotationClick(annotation: Annotation): void {
    this.selectedAnnotationId.set(annotation.id);
    this.annotationSelected.emit(annotation);
  }

  toggleReplies(annotation: Annotation, event: Event): void {
    event.stopPropagation();
    if (this.expandedAnnotation() === annotation.id) {
      this.expandedAnnotation.set(null);
    } else {
      this.expandedAnnotation.set(annotation.id);
    }
  }

  setReplyText(annotationId: number, text: string): void {
    this.replyTexts.update((texts) => ({ ...texts, [annotationId]: text }));
  }

  submitReply(annotation: Annotation): void {
    const text = this.replyTexts()[annotation.id];
    if (!text?.trim()) return;

    this.annotationService
      .createReply(this.documentId, annotation.id, text.trim())
      .subscribe({
        next: () => {
          this.replyTexts.update((texts) => {
            const copy = { ...texts };
            delete copy[annotation.id];
            return copy;
          });
          this.loadAnnotations();
        },
      });
  }

  deleteAnnotation(annotation: Annotation, event: Event): void {
    event.stopPropagation();
    if (!confirm('Delete this annotation?')) return;

    this.annotationService
      .deleteAnnotation(this.documentId, annotation.id)
      .subscribe({
        next: () => this.loadAnnotations(),
      });
  }

  getTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      highlight: 'bi-highlighter',
      underline: 'bi-type-underline',
      strikethrough: 'bi-type-strikethrough',
      sticky_note: 'bi-sticky',
      freehand: 'bi-pencil',
      rectangle: 'bi-square',
      text_box: 'bi-fonts',
      rubber_stamp: 'bi-stamp',
    };
    return icons[type] || 'bi-chat-left';
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
