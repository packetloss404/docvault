import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import { OrganizationService } from '../../services/organization.service';
import {
  ZoneOCRField,
  ZoneOCRResult,
  ZoneOCRTemplate,
} from '../../models/zone-ocr.model';
import { CustomField } from '../../models/organization.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-zone-ocr-detail',
  standalone: true,
  imports: [FormsModule, RouterLink, SubnavComponent],
  styleUrl: './zone-ocr-detail.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <div class="load-label">Loading template…</div>
          </div>
        } @else if (template()) {
          <div class="crumb">
            <a class="crumb__up" routerLink="/zone-ocr">← zone ocr templates</a>
          </div>

          <div class="dv-pagehead pagehead">
            <h1 class="dv-h1 dv-h1--sm">{{ template()!.name }}</h1>
            <span class="dv-chip">page {{ template()!.page_number }}</span>
            <span
              class="dv-chip dv-chip--upper"
              [class.dv-chip--ok]="template()!.is_active"
              [class.dv-chip--warn]="!template()!.is_active"
            >
              {{ template()!.is_active ? 'active' : 'inactive' }}
            </span>
            <button
              type="button"
              class="dv-btn dv-btn--secondary dv-btn--sm dv-push"
              (click)="editingTemplate = !editingTemplate"
            >
              {{ editingTemplate ? 'Close' : 'Edit template' }}
            </button>
          </div>

          @if (template()!.description) {
            <p class="lede">{{ template()!.description }}</p>
          }

          @if (editingTemplate) {
            <div class="dv-card dv-card--pad form-card">
              <div class="dv-card__title">Edit template</div>

              <form (ngSubmit)="saveTemplate()">
                <div class="form-grid">
                  <div>
                    <label class="dv-field__label" for="zd-name">name</label>
                    <input
                      id="zd-name"
                      type="text"
                      class="dv-input"
                      [(ngModel)]="templateName"
                      name="name"
                      required
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zd-page">page number</label>
                    <input
                      id="zd-page"
                      type="number"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="templatePageNumber"
                      name="pageNumber"
                      min="1"
                    />
                  </div>

                  <div class="form-switch">
                    <span class="dv-field__label">active</span>
                    <button
                      type="button"
                      class="dv-toggle"
                      [class.is-on]="templateIsActive"
                      [attr.aria-pressed]="templateIsActive"
                      aria-label="Active"
                      (click)="templateIsActive = !templateIsActive"
                    ></button>
                  </div>

                  <div class="form-grid__wide">
                    <label class="dv-field__label" for="zd-desc">description</label>
                    <textarea
                      id="zd-desc"
                      class="dv-input form-textarea"
                      [(ngModel)]="templateDescription"
                      name="description"
                      rows="2"
                    ></textarea>
                  </div>
                </div>

                <div class="form-actions">
                  <button type="submit" class="dv-btn dv-btn--primary dv-btn--sm">Save</button>
                  <button
                    type="button"
                    class="dv-btn dv-btn--ghost dv-btn--sm"
                    (click)="editingTemplate = false"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          }

          <!-- Sample page with zone overlay -->
          @if (template()!.sample_page_image) {
            <div class="dv-section">
              <span class="dv-eyebrow">sample page</span>
            </div>

            <div class="dv-card dv-card--pad">
              <div class="preview">
                <img
                  class="preview__img"
                  [src]="template()!.sample_page_image!"
                  alt="Sample page"
                />
                @for (field of fields(); track field.id) {
                  <div
                    class="zone"
                    [style.left.%]="field.bounding_box.x"
                    [style.top.%]="field.bounding_box.y"
                    [style.width.%]="field.bounding_box.width"
                    [style.height.%]="field.bounding_box.height"
                    [style.border-color]="getFieldColor(field.order)"
                    [style.background]="getFieldTint(field.order)"
                    [title]="field.name"
                  >
                    <span
                      class="zone__label"
                      [style.color]="getFieldColor(field.order)"
                      [style.border-color]="getFieldColor(field.order)"
                      >{{ field.name }}</span
                    >
                  </div>
                }
              </div>
            </div>
          }

          <!-- Fields -->
          <div class="dv-section">
            <span class="dv-eyebrow">zones · {{ fields().length }}</span>
            <button
              type="button"
              class="dv-btn dv-btn--accent dv-btn--sm dv-push"
              (click)="showFieldForm = !showFieldForm"
            >
              {{ showFieldForm ? 'Cancel' : '+ Add field' }}
            </button>
          </div>

          @if (showFieldForm) {
            <div class="dv-well form-card form-card--well">
              <div class="dv-card__title">{{ editingFieldId ? 'Edit field' : 'Add field' }}</div>

              <form (ngSubmit)="saveField()">
                <div class="form-grid">
                  <div>
                    <label class="dv-field__label" for="zf-name">name</label>
                    <input
                      id="zf-name"
                      type="text"
                      class="dv-input"
                      [(ngModel)]="fieldName"
                      name="fieldName"
                      required
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-type">type</label>
                    <select id="zf-type" class="dv-select" [(ngModel)]="fieldType" name="fieldType">
                      <option value="text">Text</option>
                      <option value="number">Number</option>
                      <option value="date">Date</option>
                      <option value="currency">Currency</option>
                      <option value="checkbox">Checkbox</option>
                    </select>
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-pre">preprocessing</label>
                    <select
                      id="zf-pre"
                      class="dv-select"
                      [(ngModel)]="fieldPreprocessing"
                      name="fieldPreprocessing"
                    >
                      <option value="none">None</option>
                      <option value="grayscale">Greyscale</option>
                      <option value="threshold">Threshold</option>
                      <option value="denoise">Denoise</option>
                      <option value="deskew">Deskew</option>
                    </select>
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-x">x (%)</label>
                    <input
                      id="zf-x"
                      type="number"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="fieldX"
                      name="fieldX"
                      min="0"
                      max="100"
                      step="0.1"
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-y">y (%)</label>
                    <input
                      id="zf-y"
                      type="number"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="fieldY"
                      name="fieldY"
                      min="0"
                      max="100"
                      step="0.1"
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-w">width (%)</label>
                    <input
                      id="zf-w"
                      type="number"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="fieldWidth"
                      name="fieldWidth"
                      min="0"
                      max="100"
                      step="0.1"
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-h">height (%)</label>
                    <input
                      id="zf-h"
                      type="number"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="fieldHeight"
                      name="fieldHeight"
                      min="0"
                      max="100"
                      step="0.1"
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-cf">custom field mapping</label>
                    <select
                      id="zf-cf"
                      class="dv-select"
                      [(ngModel)]="fieldCustomField"
                      name="fieldCustomField"
                    >
                      <option [ngValue]="null">— none —</option>
                      @for (cf of customFields(); track cf.id) {
                        <option [ngValue]="cf.id">{{ cf.name }} ({{ cf.data_type }})</option>
                      }
                    </select>
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-order">order</label>
                    <input
                      id="zf-order"
                      type="number"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="fieldOrder"
                      name="fieldOrder"
                      min="0"
                    />
                  </div>

                  <div>
                    <label class="dv-field__label" for="zf-regex">validation regex</label>
                    <input
                      id="zf-regex"
                      type="text"
                      class="dv-input dv-input--mono"
                      [(ngModel)]="fieldValidation"
                      name="fieldValidation"
                      placeholder="^\\d{4}-\\d{2}-\\d{2}$"
                    />
                  </div>
                </div>

                <div class="form-actions">
                  <button
                    type="submit"
                    class="dv-btn dv-btn--primary dv-btn--sm"
                    [disabled]="savingField()"
                  >
                    {{ editingFieldId ? 'Update' : 'Add' }}
                  </button>
                  <button
                    type="button"
                    class="dv-btn dv-btn--ghost dv-btn--sm"
                    (click)="cancelFieldEdit()"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          }

          <div class="list">
            <div class="dv-thead dv-grid" style="--dv-cols: 34px 1fr 96px 1.1fr 110px 130px 1fr 84px">
              <span>#</span>
              <span>name</span>
              <span>type</span>
              <span>box</span>
              <span>preprocess</span>
              <span>custom field</span>
              <span>validation</span>
              <span></span>
            </div>

            @for (field of fields(); track field.id) {
              <div
                class="dv-row dv-row--static dv-grid"
                style="--dv-cols: 34px 1fr 96px 1.1fr 110px 130px 1fr 84px"
              >
                <span
                  class="zone-index"
                  [style.color]="getFieldColor(field.order)"
                  [style.border-color]="getFieldColor(field.order)"
                  [style.background]="getFieldTint(field.order)"
                  >{{ field.order }}</span
                >
                <span class="row-name dv-clip">{{ field.name }}</span>
                <span><span class="dv-chip">{{ field.field_type }}</span></span>
                <span class="dv-meta dv-clip">
                  {{ field.bounding_box.x }},{{ field.bounding_box.y }} ·
                  {{ field.bounding_box.width }}×{{ field.bounding_box.height }}
                </span>
                <span class="dv-meta dv-clip">{{ field.preprocessing || 'none' }}</span>
                <span class="dv-muted dv-clip">{{ getCustomFieldName(field.custom_field) }}</span>
                <span class="dv-meta dv-clip">{{ field.validation_regex || '—' }}</span>
                <span class="row-actions">
                  <button type="button" class="row-action" (click)="editField(field)">edit</button>
                  <button
                    type="button"
                    class="row-action row-action--danger"
                    (click)="deleteField(field)"
                  >
                    del
                  </button>
                </span>
              </div>
            } @empty {
              <div class="dv-empty">No zones defined. Add fields to define extraction zones.</div>
            }
          </div>

          <!-- Test -->
          <div class="dv-section">
            <span class="dv-eyebrow">test template</span>
          </div>

          <div class="dv-card dv-card--pad form-card">
            <div class="test-row">
              <div class="test-row__field">
                <label class="dv-field__label" for="zd-test">document id</label>
                <input
                  id="zd-test"
                  type="number"
                  class="dv-input dv-input--mono"
                  [(ngModel)]="testDocumentId"
                  placeholder="document id to test against"
                />
              </div>
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--sm"
                (click)="runTest()"
                [disabled]="testing() || !testDocumentId"
              >
                @if (testing()) {
                  <span class="dv-spinner"></span>
                  Running…
                } @else {
                  Run test
                }
              </button>
            </div>

            @if (testResults().length > 0) {
              <div class="results">
                @for (result of testResults(); track result.id) {
                  <div class="result-row">
                    <span class="result-key">{{ result.field_name }}:</span>
                    <span class="result-value">{{ result.extracted_value || '—' }}</span>
                    <span class="dv-bar dv-bar--micro dv-push">
                      <span
                        class="dv-bar__fill"
                        [class.dv-bar__fill--ok]="result.confidence >= 0.8"
                        [class.dv-bar__fill--warn]="
                          result.confidence >= 0.5 && result.confidence < 0.8
                        "
                        [class.dv-bar__fill--danger]="result.confidence < 0.5"
                        [style.width.%]="result.confidence * 100"
                      ></span>
                    </span>
                    <span
                      class="result-conf"
                      [class.dv-ok]="result.confidence >= 0.8"
                      [class.dv-warn]="result.confidence >= 0.5 && result.confidence < 0.8"
                      [class.dv-danger]="result.confidence < 0.5"
                    >
                      {{ (result.confidence * 100).toFixed(1) }}%
                    </span>
                  </div>
                }
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class ZoneOcrDetailComponent implements OnInit {
  template = signal<ZoneOCRTemplate | null>(null);
  fields = signal<ZoneOCRField[]>([]);
  customFields = signal<CustomField[]>([]);
  loading = signal(true);
  savingField = signal(false);
  testing = signal(false);
  testResults = signal<ZoneOCRResult[]>([]);

  private templateId = 0;

  // Template edit
  editingTemplate = false;
  templateName = '';
  templateDescription = '';
  templatePageNumber = 1;
  templateIsActive = true;

  // Field form
  showFieldForm = false;
  editingFieldId: number | null = null;
  fieldName = '';
  fieldType = 'text';
  fieldX = 0;
  fieldY = 0;
  fieldWidth = 10;
  fieldHeight = 5;
  fieldCustomField: number | null = null;
  fieldOrder = 0;
  fieldPreprocessing = 'none';
  fieldValidation = '';

  // Test
  testDocumentId: number | null = null;

  // Zone accents cycle through the four semantic token hues; never literals.
  private readonly fieldColors = [
    'var(--accent)',
    'var(--ok)',
    'var(--warn)',
    'var(--danger)',
  ];

  private readonly fieldTints = [
    'var(--accent-dim)',
    'var(--ok-dim)',
    'var(--warn-dim)',
    'var(--danger-dim)',
  ];

  constructor(
    private route: ActivatedRoute,
    private zoneOcrService: ZoneOCRService,
    private orgService: OrganizationService,
  ) {}

  ngOnInit(): void {
    this.templateId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadTemplate();
    this.loadFields();
    this.loadCustomFields();
  }

  loadTemplate(): void {
    this.zoneOcrService.getTemplate(this.templateId).subscribe({
      next: (t) => {
        this.template.set(t);
        this.templateName = t.name;
        this.templateDescription = t.description;
        this.templatePageNumber = t.page_number;
        this.templateIsActive = t.is_active;
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  loadFields(): void {
    this.zoneOcrService.getFields(this.templateId).subscribe({
      next: (fields) => this.fields.set(fields),
    });
  }

  loadCustomFields(): void {
    this.orgService.getCustomFields().subscribe({
      next: (resp) => this.customFields.set(resp.results),
    });
  }

  /** Token-backed outline colour for a zone, cycling by field order. */
  getFieldColor(order: number): string {
    return this.fieldColors[order % this.fieldColors.length];
  }

  /** Matching 12–14% tint used to fill the zone overlay. */
  getFieldTint(order: number): string {
    return this.fieldTints[order % this.fieldTints.length];
  }

  getCustomFieldName(cfId: number | null): string {
    if (!cfId) return '-';
    const cf = this.customFields().find((f) => f.id === cfId);
    return cf ? cf.name : `#${cfId}`;
  }

  // Template edit

  saveTemplate(): void {
    this.zoneOcrService
      .updateTemplate(this.templateId, {
        name: this.templateName,
        description: this.templateDescription,
        page_number: this.templatePageNumber,
        is_active: this.templateIsActive,
      })
      .subscribe({
        next: () => {
          this.editingTemplate = false;
          this.loadTemplate();
        },
      });
  }

  // Field CRUD

  editField(field: ZoneOCRField): void {
    this.editingFieldId = field.id;
    this.fieldName = field.name;
    this.fieldType = field.field_type;
    this.fieldX = field.bounding_box.x;
    this.fieldY = field.bounding_box.y;
    this.fieldWidth = field.bounding_box.width;
    this.fieldHeight = field.bounding_box.height;
    this.fieldCustomField = field.custom_field;
    this.fieldOrder = field.order;
    this.fieldPreprocessing = field.preprocessing;
    this.fieldValidation = field.validation_regex;
    this.showFieldForm = true;
  }

  cancelFieldEdit(): void {
    this.editingFieldId = null;
    this.fieldName = '';
    this.fieldType = 'text';
    this.fieldX = 0;
    this.fieldY = 0;
    this.fieldWidth = 10;
    this.fieldHeight = 5;
    this.fieldCustomField = null;
    this.fieldOrder = this.fields().length;
    this.fieldPreprocessing = 'none';
    this.fieldValidation = '';
    this.showFieldForm = false;
  }

  saveField(): void {
    if (!this.fieldName.trim()) return;
    this.savingField.set(true);

    const data: Partial<ZoneOCRField> = {
      name: this.fieldName.trim(),
      field_type: this.fieldType,
      bounding_box: {
        x: this.fieldX,
        y: this.fieldY,
        width: this.fieldWidth,
        height: this.fieldHeight,
      },
      custom_field: this.fieldCustomField,
      order: this.fieldOrder,
      preprocessing: this.fieldPreprocessing,
      validation_regex: this.fieldValidation,
    };

    const request = this.editingFieldId
      ? this.zoneOcrService.updateField(this.templateId, this.editingFieldId, data)
      : this.zoneOcrService.createField(this.templateId, data);

    request.subscribe({
      next: () => {
        this.savingField.set(false);
        this.cancelFieldEdit();
        this.loadFields();
      },
      error: () => this.savingField.set(false),
    });
  }

  deleteField(field: ZoneOCRField): void {
    if (!confirm(`Delete field "${field.name}"?`)) return;
    this.zoneOcrService.deleteField(this.templateId, field.id).subscribe({
      next: () => this.loadFields(),
    });
  }

  // Test

  runTest(): void {
    if (!this.testDocumentId) return;
    this.testing.set(true);
    this.zoneOcrService
      .testTemplate(this.templateId, this.testDocumentId)
      .subscribe({
        next: (results) => {
          this.testResults.set(results);
          this.testing.set(false);
        },
        error: () => this.testing.set(false),
      });
  }
}
