import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import { ZoneOCRTemplate } from '../../models/zone-ocr.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-zone-ocr-templates',
  standalone: true,
  imports: [DatePipe, FormsModule, RouterLink, SubnavComponent],
  styleUrl: './zone-ocr-templates.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-pagehead pagehead">
          <h1 class="dv-h1 dv-h1--sm">Zone OCR templates</h1>
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--sm dv-push"
            (click)="showForm = !showForm"
          >
            {{ showForm ? 'Cancel' : '+ New template' }}
          </button>
        </div>

        @if (showForm) {
          <div class="dv-card dv-card--pad form-card">
            <div class="dv-card__title">{{ editingId ? 'Edit template' : 'New template' }}</div>

            <form (ngSubmit)="onSave()">
              <div class="form-grid">
                <div>
                  <label class="dv-field__label" for="zt-name">name</label>
                  <input
                    id="zt-name"
                    type="text"
                    class="dv-input"
                    [(ngModel)]="formName"
                    name="name"
                    required
                  />
                </div>

                <div>
                  <label class="dv-field__label" for="zt-page">page number</label>
                  <input
                    id="zt-page"
                    type="number"
                    class="dv-input dv-input--mono"
                    [(ngModel)]="formPageNumber"
                    name="pageNumber"
                    min="1"
                  />
                </div>

                <div class="form-switch">
                  <span class="dv-field__label">active</span>
                  <button
                    type="button"
                    class="dv-toggle"
                    [class.is-on]="formIsActive"
                    [attr.aria-pressed]="formIsActive"
                    aria-label="Active"
                    (click)="formIsActive = !formIsActive"
                  ></button>
                </div>

                <div class="form-grid__wide">
                  <label class="dv-field__label" for="zt-desc">description</label>
                  <textarea
                    id="zt-desc"
                    class="dv-input form-textarea"
                    [(ngModel)]="formDescription"
                    name="description"
                    rows="2"
                  ></textarea>
                </div>
              </div>

              <div class="form-actions">
                <button
                  type="submit"
                  class="dv-btn dv-btn--primary dv-btn--sm"
                  [disabled]="saving()"
                >
                  {{ editingId ? 'Update' : 'Create' }}
                </button>
                <button
                  type="button"
                  class="dv-btn dv-btn--ghost dv-btn--sm"
                  (click)="cancelEdit()"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        }

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <div class="load-label">Loading templates…</div>
          </div>
        } @else {
          <div class="dv-section">
            <span class="dv-eyebrow">zone templates</span>
          </div>

          <div class="list">
            <div class="dv-thead dv-grid" style="--dv-cols: 1fr 1.1fr 80px 96px 96px 118px 84px">
              <span>name</span>
              <span>description</span>
              <span>page</span>
              <span>zones</span>
              <span>state</span>
              <span class="dv-num">created</span>
              <span></span>
            </div>

            @for (template of templates(); track template.id) {
              <div
                class="dv-row dv-row--static dv-grid"
                style="--dv-cols: 1fr 1.1fr 80px 96px 96px 118px 84px"
              >
                <a class="row-name dv-clip" [routerLink]="['/zone-ocr', template.id]">
                  {{ template.name }}
                </a>
                <span class="dv-muted dv-clip">
                  {{ template.description || '—' }}
                </span>
                <span class="dv-ts">p{{ template.page_number }}</span>
                <span class="dv-ts">{{ template.field_count }} zones</span>
                <span class="row-state" [class.row-state--on]="template.is_active">
                  {{ template.is_active ? '● active' : '○ inactive' }}
                </span>
                <span class="dv-ts dv-num">{{ template.created_at | date: 'yyyy-MM-dd' }}</span>
                <span class="row-actions">
                  <button type="button" class="row-action" (click)="onEdit(template)">edit</button>
                  <button
                    type="button"
                    class="row-action row-action--danger"
                    (click)="onDelete(template)"
                  >
                    del
                  </button>
                </span>
              </div>
            } @empty {
              <div class="dv-empty">
                No Zone OCR templates yet. Create one to get started.
              </div>
            }
          </div>
        }
      </div>
    </div>

    @if (deleteConfirm) {
      <div class="dv-overlay" (click)="deleteConfirm = null">
        <div class="dv-card dv-card--r14 dv-card--pad confirm" (click)="$event.stopPropagation()">
          <div class="dv-h2">Delete template</div>
          <p class="confirm__body">
            Delete <span class="dv-mono">{{ deleteConfirm.name }}</span>? This also deletes all
            associated fields and extraction results.
          </p>
          <div class="form-actions">
            <button
              type="button"
              class="dv-btn dv-btn--ghost dv-btn--sm"
              (click)="deleteConfirm = null"
            >
              Cancel
            </button>
            <button
              type="button"
              class="dv-btn dv-btn--danger dv-btn--sm"
              (click)="confirmDelete()"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ZoneOcrTemplatesComponent implements OnInit {
  templates = signal<ZoneOCRTemplate[]>([]);
  loading = signal(true);
  saving = signal(false);

  showForm = false;
  editingId: number | null = null;
  formName = '';
  formDescription = '';
  formPageNumber = 1;
  formIsActive = true;
  deleteConfirm: ZoneOCRTemplate | null = null;

  constructor(private zoneOcrService: ZoneOCRService) {}

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.zoneOcrService.getTemplates().subscribe({
      next: (response) => {
        this.templates.set(response.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onEdit(template: ZoneOCRTemplate): void {
    this.editingId = template.id;
    this.formName = template.name;
    this.formDescription = template.description;
    this.formPageNumber = template.page_number;
    this.formIsActive = template.is_active;
    this.showForm = true;
  }

  cancelEdit(): void {
    this.editingId = null;
    this.formName = '';
    this.formDescription = '';
    this.formPageNumber = 1;
    this.formIsActive = true;
    this.showForm = false;
  }

  onSave(): void {
    if (!this.formName.trim()) return;
    this.saving.set(true);
    const data: Partial<ZoneOCRTemplate> = {
      name: this.formName.trim(),
      description: this.formDescription.trim(),
      page_number: this.formPageNumber,
      is_active: this.formIsActive,
    };

    const request = this.editingId
      ? this.zoneOcrService.updateTemplate(this.editingId, data)
      : this.zoneOcrService.createTemplate(data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.cancelEdit();
        this.loadTemplates();
      },
      error: () => this.saving.set(false),
    });
  }

  onDelete(template: ZoneOCRTemplate): void {
    this.deleteConfirm = template;
  }

  confirmDelete(): void {
    if (!this.deleteConfirm) return;
    this.zoneOcrService.deleteTemplate(this.deleteConfirm.id).subscribe({
      next: () => {
        this.deleteConfirm = null;
        this.loadTemplates();
      },
    });
  }
}
