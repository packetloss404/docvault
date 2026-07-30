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
    <div class="ap">
      @if (loading()) {
        <div class="dv-empty ap__empty">
          <span class="dv-spinner"></span>
          <span class="dv-sr">Loading annotations…</span>
        </div>
      } @else if (annotations().length === 0) {
        <div class="dv-empty ap__empty">No annotations on this page.</div>
      } @else {
        @for (annotation of annotations(); track annotation.id) {
          <div
            class="dv-card dv-card--r9 ap__item"
            [class.is-selected]="selectedAnnotationId() === annotation.id"
            (click)="onAnnotationClick(annotation)"
          >
            <div class="ap__meta">
              <span
                class="ap__swatch"
                [style.background]="annotation.color"
                [style.opacity]="annotation.opacity"
                aria-hidden="true"
              ></span>
              <span class="ap__author">{{ annotation.author_name }}</span>
              <span class="dv-chip dv-chip--upper ap__kind">{{
                typeLabel(annotation.annotation_type)
              }}</span>
              @if (annotation.is_private) {
                <span class="dv-chip dv-chip--upper dv-chip--warn">private</span>
              }
              <button
                type="button"
                class="ap__del dv-push"
                title="Delete annotation"
                (click)="deleteAnnotation(annotation, $event)"
              >
                <span aria-hidden="true">✕</span>
                <span class="dv-sr">Delete annotation</span>
              </button>
            </div>

            <div class="dv-meta ap__when">{{ formatDate(annotation.created_at) }}</div>

            @if (annotation.content) {
              <div class="ap__text">{{ annotation.content }}</div>
            }

            @if (annotation.reply_count > 0) {
              <button
                type="button"
                class="dv-link ap__toggle"
                (click)="toggleReplies(annotation, $event)"
              >
                {{ expandedAnnotation() === annotation.id ? '▾' : '▸' }}
                {{ annotation.reply_count }}
                {{ annotation.reply_count === 1 ? 'reply' : 'replies' }}
              </button>
            }

            @if (expandedAnnotation() === annotation.id) {
              <div class="ap__replies">
                @for (reply of annotation.replies; track reply.id) {
                  <div class="ap__reply">
                    <div class="ap__replymeta">
                      <span class="ap__replyauthor">{{ reply.author_name }}</span>
                      <span class="dv-meta dv-push">{{
                        formatDate(reply.created_at)
                      }}</span>
                    </div>
                    <div class="ap__text">{{ reply.text }}</div>
                  </div>
                }
              </div>
            }

            @if (
              expandedAnnotation() === annotation.id || annotation.reply_count === 0
            ) {
              <div class="ap__compose">
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  placeholder="Reply…"
                  aria-label="Add a reply"
                  [ngModel]="replyTexts()[annotation.id] || ''"
                  (ngModelChange)="setReplyText(annotation.id, $event)"
                  (keyup.enter)="submitReply(annotation)"
                  (click)="$event.stopPropagation()"
                />
                <button
                  type="button"
                  class="dv-btn dv-btn--ghost ap__send"
                  title="Post reply"
                  [disabled]="!replyTexts()[annotation.id]"
                  (click)="submitReply(annotation); $event.stopPropagation()"
                >
                  <span aria-hidden="true">↵</span>
                  <span class="dv-sr">Post reply</span>
                </button>
              </div>
            }
          </div>
        }
      }
    </div>
  `,
  styleUrl: './annotation-panel.component.scss',
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

  /** Text glyph standing in for an annotation type (Console uses no icon font). */
  getTypeIcon(type: string): string {
    const glyphs: Record<string, string> = {
      highlight: '▮',
      underline: '﹍',
      strikethrough: '⌦',
      sticky_note: '📌',
      freehand: '✎',
      rectangle: '▢',
      text_box: 'T',
      rubber_stamp: '⧉',
    };
    return glyphs[type] || '•';
  }

  /** Short mono-chip label for an annotation type. */
  typeLabel(type: string): string {
    const labels: Record<string, string> = {
      highlight: 'highlight',
      underline: 'underline',
      strikethrough: 'strike',
      sticky_note: 'note',
      freehand: 'draw',
      rectangle: 'box',
      text_box: 'text',
      rubber_stamp: 'stamp',
    };
    return labels[type] || type.replace(/_/g, ' ');
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
