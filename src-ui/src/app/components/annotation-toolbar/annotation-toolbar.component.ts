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
    <div class="d-flex align-items-center gap-2 p-2 border rounded bg-light flex-wrap">
      <!-- Tool Buttons -->
      <div class="btn-group btn-group-sm" role="group" aria-label="Annotation tools">
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'highlight' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Highlight"
          (click)="selectTool('highlight')"
        >
          <i class="bi bi-highlighter"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'underline' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Underline"
          (click)="selectTool('underline')"
        >
          <i class="bi bi-type-underline"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'strikethrough' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Strikethrough"
          (click)="selectTool('strikethrough')"
        >
          <i class="bi bi-type-strikethrough"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'sticky_note' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Sticky Note"
          (click)="selectTool('sticky_note')"
        >
          <i class="bi bi-sticky"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'freehand' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Freehand"
          (click)="selectTool('freehand')"
        >
          <i class="bi bi-pencil"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'rectangle' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Rectangle"
          (click)="selectTool('rectangle')"
        >
          <i class="bi bi-square"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'text_box' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Text Box"
          (click)="selectTool('text_box')"
        >
          <i class="bi bi-fonts"></i>
        </button>
        <button
          type="button"
          class="btn"
          [ngClass]="activeTool() === 'rubber_stamp' ? 'btn-warning' : 'btn-outline-secondary'"
          title="Rubber Stamp"
          (click)="selectTool('rubber_stamp')"
        >
          <i class="bi bi-stamp"></i>
        </button>
      </div>

      <div class="vr"></div>

      <!-- Color Picker -->
      <div class="d-flex align-items-center gap-1">
        <label class="form-label mb-0 small text-muted">Color</label>
        <input
          type="color"
          class="form-control form-control-color form-control-sm"
          [ngModel]="color()"
          (ngModelChange)="onColorChange($event)"
          title="Annotation color"
          style="width: 32px; height: 32px;"
        />
      </div>

      <!-- Opacity Slider -->
      <div class="d-flex align-items-center gap-1">
        <label class="form-label mb-0 small text-muted">Opacity</label>
        <input
          type="range"
          class="form-range"
          min="0.1"
          max="1.0"
          step="0.1"
          [ngModel]="opacity()"
          (ngModelChange)="onOpacityChange($event)"
          title="Annotation opacity"
          style="width: 80px;"
        />
        <span class="small text-muted">{{ (opacity() * 100).toFixed(0) }}%</span>
      </div>

      <div class="vr"></div>

      <!-- Visibility Toggle -->
      <button
        class="btn btn-sm"
        [ngClass]="annotationsVisible() ? 'btn-outline-primary' : 'btn-outline-secondary'"
        title="Toggle annotation visibility"
        (click)="toggleVisibility()"
      >
        <i class="bi" [ngClass]="annotationsVisible() ? 'bi-eye' : 'bi-eye-slash'"></i>
      </button>

      <!-- Author Filter -->
      <div class="d-flex align-items-center gap-1">
        <select
          class="form-select form-select-sm"
          style="width: auto;"
          [ngModel]="authorFilter()"
          (ngModelChange)="onAuthorFilterChange($event)"
        >
          <option value="">All Authors</option>
          @for (author of authors; track author) {
            <option [value]="author">{{ author }}</option>
          }
        </select>
      </div>

      <!-- Export Button -->
      <button
        class="btn btn-sm btn-outline-success"
        title="Export annotations"
        (click)="onExport()"
      >
        <i class="bi bi-download me-1"></i>Export
      </button>
    </div>
  `,
})
export class AnnotationToolbarComponent implements OnInit {
  @Input() documentId = 0;
  @Input() authors: string[] = [];

  @Output() toolSelected = new EventEmitter<AnnotationToolSelection>();
  @Output() visibilityChanged = new EventEmitter<boolean>();
  @Output() authorFilterChanged = new EventEmitter<string>();
  @Output() exportRequested = new EventEmitter<void>();

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
