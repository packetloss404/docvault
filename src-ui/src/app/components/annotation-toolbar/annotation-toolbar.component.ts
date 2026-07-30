import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AnnotationService } from '../../services/annotation.service';

export interface AnnotationToolSelection {
  tool: string;
  color: string;
  opacity: number;
}

@Component({
  selector: 'app-annotation-toolbar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="at">
      <div class="at__tools" role="group" aria-label="Annotation tools">
        @for (tool of tools; track tool.id) {
          <button
            type="button"
            class="dv-btn dv-btn--ghost dv-btn--sm at__tool"
            [class.is-active]="activeTool() === tool.id"
            [title]="tool.label"
            [attr.aria-pressed]="activeTool() === tool.id"
            (click)="selectTool(tool.id)"
          >
            <span aria-hidden="true">{{ tool.glyph }}</span>
            <span class="dv-sr">{{ tool.label }}</span>
          </button>
        }
      </div>

      <span class="at__sep" aria-hidden="true"></span>

      <label class="at__group">
        <span class="dv-eyebrow">colour</span>
        <input
          type="color"
          class="at__color"
          [ngModel]="color()"
          (ngModelChange)="onColorChange($event)"
          title="Annotation colour"
        />
      </label>

      <label class="at__group">
        <span class="dv-eyebrow">opacity</span>
        <input
          type="range"
          class="at__range"
          min="0.1"
          max="1.0"
          step="0.1"
          [ngModel]="opacity()"
          (ngModelChange)="onOpacityChange($event)"
          title="Annotation opacity"
        />
        <span class="dv-meta at__pct">{{ (opacity() * 100).toFixed(0) }}%</span>
      </label>

      <span class="at__sep" aria-hidden="true"></span>

      <button
        type="button"
        class="dv-btn dv-btn--ghost dv-btn--sm at__tool"
        [class.is-active]="annotationsVisible()"
        [attr.aria-pressed]="annotationsVisible()"
        title="Toggle annotation visibility"
        (click)="toggleVisibility()"
      >
        <span aria-hidden="true">{{ annotationsVisible() ? '◉' : '◌' }}</span>
        <span class="dv-sr">Toggle annotation visibility</span>
      </button>

      <select
        class="dv-input dv-input--r7 at__authors"
        aria-label="Filter annotations by author"
        [ngModel]="authorFilter()"
        (ngModelChange)="onAuthorFilterChange($event)"
      >
        <option value="">all authors</option>
        @for (author of authors; track author) {
          <option [value]="author">{{ author }}</option>
        }
      </select>

      <button
        type="button"
        class="dv-btn dv-btn--ghost dv-btn--sm dv-push"
        title="Export annotations"
        (click)="onExport()"
      >
        ↓ export
      </button>
    </div>
  `,
  styleUrl: './annotation-toolbar.component.scss',
})
export class AnnotationToolbarComponent implements OnInit {
  @Input() documentId = 0;
  @Input() authors: string[] = [];

  @Output() toolSelected = new EventEmitter<AnnotationToolSelection>();
  @Output() visibilityChanged = new EventEmitter<boolean>();
  @Output() authorFilterChanged = new EventEmitter<string>();
  @Output() exportRequested = new EventEmitter<void>();

  /** Tool palette. Console has no icon font, so each tool carries a glyph. */
  readonly tools: { id: string; label: string; glyph: string }[] = [
    { id: 'highlight', label: 'Highlight', glyph: '▮' },
    { id: 'underline', label: 'Underline', glyph: '﹍' },
    { id: 'strikethrough', label: 'Strikethrough', glyph: '⌦' },
    { id: 'sticky_note', label: 'Sticky note', glyph: '📌' },
    { id: 'freehand', label: 'Freehand', glyph: '✎' },
    { id: 'rectangle', label: 'Rectangle', glyph: '▢' },
    { id: 'text_box', label: 'Text box', glyph: 'T' },
    { id: 'rubber_stamp', label: 'Rubber stamp', glyph: '⧉' },
  ];

  activeTool = signal('');
  color = signal('#FFFF00');
  opacity = signal(0.3);
  annotationsVisible = signal(true);
  authorFilter = signal('');

  constructor(private annotationService: AnnotationService) {}

  ngOnInit(): void {}

  selectTool(tool: string): void {
    if (this.activeTool() === tool) {
      this.activeTool.set('');
    } else {
      this.activeTool.set(tool);
    }
    this.emitToolSelection();
  }

  onColorChange(value: string): void {
    this.color.set(value);
    this.emitToolSelection();
  }

  onOpacityChange(value: number): void {
    this.opacity.set(Number(value));
    this.emitToolSelection();
  }

  toggleVisibility(): void {
    this.annotationsVisible.update((v) => !v);
    this.visibilityChanged.emit(this.annotationsVisible());
  }

  onAuthorFilterChange(value: string): void {
    this.authorFilter.set(value);
    this.authorFilterChanged.emit(value);
  }

  onExport(): void {
    this.exportRequested.emit();
  }

  private emitToolSelection(): void {
    this.toolSelected.emit({
      tool: this.activeTool(),
      color: this.color(),
      opacity: this.opacity(),
    });
  }
}
