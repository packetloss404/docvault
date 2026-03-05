import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import { OrganizationService } from '../../services/organization.service';
import {
  ZoneOCRField,
  ZoneOCRResult,
  ZoneOCRTemplate,
} from '../../models/zone-ocr.model';
import { CustomField } from '../../models/organization.model';

@Component({
  selector: 'app-zone-ocr-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    @if (loading()) {
      <div class="text-center py-5">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (template()) {
      <!-- Header -->
      <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
          <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
              <li class="breadcrumb-item"><a routerLink="/zone-ocr">Zone OCR Templates</a></li>
              <li class="breadcrumb-item active">{{ template()!.name }}</li>
            </ol>
          </nav>
          <h2>{{ template()!.name }}</h2>
          @if (template()!.description) {
            <p class="text-muted">{{ template()!.description }}</p>
          }
          <div class="d-flex gap-2">
            <span class="badge bg-info">Page {{ template()!.page_number }}</span>
            @if (template()!.is_active) {
              <span class="badge bg-success">Active</span>
            } @else {
              <span class="badge bg-warning text-dark">Inactive</span>
            }
          </div>
        </div>
        <button class="btn btn-outline-primary" (click)="editingTemplate = !editingTemplate">
          <i class="bi bi-pencil me-1"></i>Edit Template
        </button>
      </div>

      @if (editingTemplate) {
        <div class="card mb-4">
          <div class="card-body">
            <h5 class="card-title">Edit Template</h5>
            <form (ngSubmit)="saveTemplate()">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">Name</label>
                  <input type="text" class="form-control" [(ngModel)]="templateName" name="name" required />
                </div>
                <div class="col-md-3">
                  <label class="form-label">Page Number</label>
                  <input type="number" class="form-control" [(ngModel)]="templatePageNumber" name="pageNumber" min="1" />
                </div>
                <div class="col-md-3 d-flex align-items-end">
                  <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" [(ngModel)]="templateIsActive" name="isActive" id="editActiveSwitch" />
                    <label class="form-check-label" for="editActiveSwitch">Active</label>
                  </div>
                </div>
                <div class="col-12">
                  <label class="form-label">Description</label>
                  <textarea class="form-control" [(ngModel)]="templateDescription" name="description" rows="2"></textarea>
                </div>
                <div class="col-12">
                  <button type="submit" class="btn btn-success me-2">
                    <i class="bi bi-check-lg me-1"></i>Save
                  </button>
                  <button type="button" class="btn btn-secondary" (click)="editingTemplate = false">Cancel</button>
                </div>
              </div>
            </form>
          </div>
        </div>
      }

      <!-- Sample Image with Bounding Box Overlay -->
      @if (template()!.sample_page_image) {
        <div class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0">Sample Page Preview</h5>
          </div>
          <div class="card-body">
            <div class="position-relative d-inline-block" style="max-width: 100%;">
              <img
                [src]="template()!.sample_page_image!"
                alt="Sample page"
                class="img-fluid border"
                style="max-height: 600px;"
              />
              @for (field of fields(); track field.id) {
                <div
                  class="position-absolute border border-2"
                  [style.left.%]="field.bounding_box.x"
                  [style.top.%]="field.bounding_box.y"
                  [style.width.%]="field.bounding_box.width"
                  [style.height.%]="field.bounding_box.height"
                  [style.border-color]="getFieldColor(field.order)"
                  [style.background]="getFieldColor(field.order) + '20'"
                  [title]="field.name"
                >
                  <span
                    class="position-absolute text-white px-1 small"
                    style="top: -18px; left: 0; font-size: 0.7rem;"
                    [style.background]="getFieldColor(field.order)"
                  >
                    {{ field.name }}
                  </span>
                </div>
              }
            </div>
          </div>
        </div>
      }

      <!-- Fields Section -->
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Fields ({{ fields().length }})</h5>
          <button class="btn btn-sm btn-primary" (click)="showFieldForm = !showFieldForm">
            <i class="bi bi-plus-lg me-1"></i>Add Field
          </button>
        </div>
        <div class="card-body">
          @if (showFieldForm) {
            <div class="border rounded p-3 mb-3 bg-light">
              <h6>{{ editingFieldId ? 'Edit' : 'Add' }} Field</h6>
              <form (ngSubmit)="saveField()">
                <div class="row g-3">
                  <div class="col-md-4">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-control" [(ngModel)]="fieldName" name="fieldName" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Type</label>
                    <select class="form-select" [(ngModel)]="fieldType" name="fieldType">
                      <option value="text">Text</option>
                      <option value="number">Number</option>
                      <option value="date">Date</option>
                      <option value="currency">Currency</option>
                      <option value="checkbox">Checkbox</option>
                    </select>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Preprocessing</label>
                    <select class="form-select" [(ngModel)]="fieldPreprocessing" name="fieldPreprocessing">
                      <option value="none">None</option>
                      <option value="grayscale">Grayscale</option>
                      <option value="threshold">Threshold</option>
                      <option value="denoise">Denoise</option>
                      <option value="deskew">Deskew</option>
                    </select>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">X (%)</label>
                    <input type="number" class="form-control" [(ngModel)]="fieldX" name="fieldX" min="0" max="100" step="0.1" />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Y (%)</label>
                    <input type="number" class="form-control" [(ngModel)]="fieldY" name="fieldY" min="0" max="100" step="0.1" />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Width (%)</label>
                    <input type="number" class="form-control" [(ngModel)]="fieldWidth" name="fieldWidth" min="0" max="100" step="0.1" />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Height (%)</label>
                    <input type="number" class="form-control" [(ngModel)]="fieldHeight" name="fieldHeight" min="0" max="100" step="0.1" />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Custom Field Mapping</label>
                    <select class="form-select" [(ngModel)]="fieldCustomField" name="fieldCustomField">
                      <option [ngValue]="null">-- None --</option>
                      @for (cf of customFields(); track cf.id) {
                        <option [ngValue]="cf.id">{{ cf.name }} ({{ cf.data_type }})</option>
                      }
                    </select>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Order</label>
                    <input type="number" class="form-control" [(ngModel)]="fieldOrder" name="fieldOrder" min="0" />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Validation Regex</label>
                    <input type="text" class="form-control" [(ngModel)]="fieldValidation" name="fieldValidation" placeholder="e.g. ^\\d{4}-\\d{2}-\\d{2}$" />
                  </div>
                  <div class="col-12">
                    <button type="submit" class="btn btn-success btn-sm me-2" [disabled]="savingField()">
                      <i class="bi bi-check-lg me-1"></i>{{ editingFieldId ? 'Update' : 'Add' }}
                    </button>
                    <button type="button" class="btn btn-secondary btn-sm" (click)="cancelFieldEdit()">Cancel</button>
                  </div>
                </div>
              </form>
            </div>
          }

          <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th style="width: 30px;">#</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Bounding Box</th>
                  <th>Preprocessing</th>
                  <th>Custom Field</th>
                  <th>Validation</th>
                  <th class="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (field of fields(); track field.id) {
                  <tr>
                    <td>
                      <span class="badge rounded-pill" [style.background]="getFieldColor(field.order)">{{ field.order }}</span>
                    </td>
                    <td class="fw-semibold">{{ field.name }}</td>
                    <td><span class="badge bg-secondary">{{ field.field_type }}</span></td>
                    <td class="small text-muted">
                      {{ field.bounding_box.x }}%, {{ field.bounding_box.y }}% / {{ field.bounding_box.width }}% x {{ field.bounding_box.height }}%
                    </td>
                    <td>{{ field.preprocessing || 'none' }}</td>
                    <td>{{ getCustomFieldName(field.custom_field) }}</td>
                    <td class="small text-muted">{{ field.validation_regex || '-' }}</td>
                    <td class="text-end">
                      <button class="btn btn-sm btn-outline-primary me-1" (click)="editField(field)" title="Edit">
                        <i class="bi bi-pencil"></i>
                      </button>
                      <button class="btn btn-sm btn-outline-danger" (click)="deleteField(field)" title="Delete">
                        <i class="bi bi-trash"></i>
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="8" class="text-center text-muted py-3">
                      No fields defined. Add fields to define extraction zones.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Test Section -->
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0">Test Template</h5>
        </div>
        <div class="card-body">
          <div class="row g-3 align-items-end">
            <div class="col-md-6">
              <label class="form-label">Document ID</label>
              <input
                type="number"
                class="form-control"
                [(ngModel)]="testDocumentId"
                placeholder="Enter document ID to test against"
              />
            </div>
            <div class="col-md-3">
              <button
                class="btn btn-warning"
                (click)="runTest()"
                [disabled]="testing() || !testDocumentId"
              >
                @if (testing()) {
                  <span class="spinner-border spinner-border-sm me-1"></span>
                } @else {
                  <i class="bi bi-play-fill me-1"></i>
                }
                Run Test
              </button>
            </div>
          </div>

          @if (testResults().length > 0) {
            <div class="mt-3">
              <h6>Test Results</h6>
              <div class="table-responsive">
                <table class="table table-sm">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Extracted Value</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (result of testResults(); track result.id) {
                      <tr>
                        <td>{{ result.field_name }}</td>
                        <td><code>{{ result.extracted_value }}</code></td>
                        <td>
                          <div class="d-flex align-items-center gap-2">
                            <div class="progress flex-grow-1" style="height: 6px;">
                              <div
                                class="progress-bar"
                                [class.bg-success]="result.confidence >= 0.8"
                                [class.bg-warning]="result.confidence >= 0.5 && result.confidence < 0.8"
                                [class.bg-danger]="result.confidence < 0.5"
                                [style.width.%]="result.confidence * 100"
                              ></div>
                            </div>
                            <span class="small">{{ (result.confidence * 100).toFixed(1) }}%</span>
                          </div>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }
        </div>
      </div>
    }
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

  private readonly fieldColors = [
    '#0d6efd', '#198754', '#dc3545', '#ffc107', '#0dcaf0',
    '#6f42c1', '#fd7e14', '#d63384', '#20c997', '#6610f2',
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

  getFieldColor(order: number): string {
    return this.fieldColors[order % this.fieldColors.length];
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
