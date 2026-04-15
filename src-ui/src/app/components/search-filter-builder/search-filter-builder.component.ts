import { Component, EventEmitter, OnInit, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export type FilterField =
  | 'title'
  | 'content'
  | 'document_type'
  | 'correspondent'
  | 'tags'
  | 'created'
  | 'language';

export type FilterOperator =
  | 'contains'
  | 'equals'
  | 'starts_with'
  | 'date_before'
  | 'date_after';

export interface FilterRow {
  field: FilterField;
  operator: FilterOperator;
  value: string;
}

export const FILTER_FIELDS: { value: FilterField; label: string }[] = [
  { value: 'title', label: 'Title' },
  { value: 'content', label: 'Content' },
  { value: 'document_type', label: 'Document Type' },
  { value: 'correspondent', label: 'Correspondent' },
  { value: 'tags', label: 'Tags' },
  { value: 'created', label: 'Created (date)' },
  { value: 'language', label: 'Language' },
];

export const FILTER_OPERATORS: { value: FilterOperator; label: string; forDate?: boolean }[] = [
  { value: 'contains', label: 'Contains' },
  { value: 'equals', label: 'Equals' },
  { value: 'starts_with', label: 'Starts with' },
  { value: 'date_before', label: 'Date before', forDate: true },
  { value: 'date_after', label: 'Date after', forDate: true },
];

const DATE_FIELDS: FilterField[] = ['created'];

function defaultOperatorForField(field: FilterField): FilterOperator {
  return DATE_FIELDS.includes(field) ? 'date_after' : 'contains';
}

@Component({
  selector: 'app-search-filter-builder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center py-2">
        <h6 class="mb-0">
          <i class="bi bi-funnel me-1"></i>Filter Builder
        </h6>
        <button class="btn btn-sm btn-outline-primary" (click)="addRow()">
          <i class="bi bi-plus-lg me-1"></i>Add Filter
        </button>
      </div>

      @if (rows().length > 0) {
        <div class="card-body pb-2">
          @for (row of rows(); track $index; let i = $index) {
            <div class="row g-2 align-items-center mb-2">
              <!-- Field -->
              <div class="col-md-3">
                <select
                  class="form-select form-select-sm"
                  [ngModel]="row.field"
                  (ngModelChange)="onFieldChange(i, $event)"
                >
                  @for (f of fields; track f.value) {
                    <option [value]="f.value">{{ f.label }}</option>
                  }
                </select>
              </div>

              <!-- Operator -->
              <div class="col-md-3">
                <select
                  class="form-select form-select-sm"
                  [ngModel]="row.operator"
                  (ngModelChange)="onOperatorChange(i, $event)"
                >
                  @for (op of operatorsFor(row.field); track op.value) {
                    <option [value]="op.value">{{ op.label }}</option>
                  }
                </select>
              </div>

              <!-- Value -->
              <div class="col-md-5">
                @if (isDateField(row.field)) {
                  <input
                    type="date"
                    class="form-control form-control-sm"
                    [ngModel]="row.value"
                    (ngModelChange)="onValueChange(i, $event)"
                  />
                } @else {
                  <input
                    type="text"
                    class="form-control form-control-sm"
                    placeholder="Value…"
                    [ngModel]="row.value"
                    (ngModelChange)="onValueChange(i, $event)"
                    (keyup.enter)="emitFilters()"
                  />
                }
              </div>

              <!-- Remove -->
              <div class="col-md-1 text-end">
                <button
                  class="btn btn-sm btn-outline-danger"
                  title="Remove filter"
                  (click)="removeRow(i)"
                >
                  <i class="bi bi-x-lg"></i>
                </button>
              </div>
            </div>
          }

          <div class="d-flex justify-content-end gap-2 mt-1 mb-1">
            <button class="btn btn-sm btn-outline-secondary" (click)="clearAll()">
              Clear All
            </button>
            <button class="btn btn-sm btn-primary" (click)="emitFilters()">
              <i class="bi bi-search me-1"></i>Apply Filters
            </button>
          </div>
        </div>
      } @else {
        <div class="card-body text-muted small py-2">
          No filters added. Click <strong>Add Filter</strong> to narrow results.
        </div>
      }
    </div>
  `,
})
export class SearchFilterBuilderComponent implements OnInit {
  @Output() filtersChange = new EventEmitter<FilterRow[]>();

  rows = signal<FilterRow[]>([]);

  readonly fields = FILTER_FIELDS;
  readonly allOperators = FILTER_OPERATORS;

  ngOnInit(): void {}

  operatorsFor(field: FilterField): typeof FILTER_OPERATORS {
    if (DATE_FIELDS.includes(field)) {
      return this.allOperators.filter((op) => op.forDate);
    }
    return this.allOperators.filter((op) => !op.forDate);
  }

  isDateField(field: FilterField): boolean {
    return DATE_FIELDS.includes(field);
  }

  addRow(): void {
    const field: FilterField = 'title';
    this.rows.update((rows) => [
      ...rows,
      { field, operator: defaultOperatorForField(field), value: '' },
    ]);
  }

  removeRow(index: number): void {
    this.rows.update((rows) => rows.filter((_, i) => i !== index));
    this.emitFilters();
  }

  onFieldChange(index: number, newField: FilterField): void {
    this.rows.update((rows) =>
      rows.map((row, i) =>
        i === index
          ? { ...row, field: newField, operator: defaultOperatorForField(newField), value: '' }
          : row,
      ),
    );
  }

  onOperatorChange(index: number, newOperator: FilterOperator): void {
    this.rows.update((rows) =>
      rows.map((row, i) => (i === index ? { ...row, operator: newOperator } : row)),
    );
  }

  onValueChange(index: number, newValue: string): void {
    this.rows.update((rows) =>
      rows.map((row, i) => (i === index ? { ...row, value: newValue } : row)),
    );
  }

  clearAll(): void {
    this.rows.set([]);
    this.filtersChange.emit([]);
  }

  emitFilters(): void {
    const active = this.rows().filter((r) => r.value.trim() !== '');
    this.filtersChange.emit(active);
  }
}
