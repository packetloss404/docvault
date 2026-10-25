import { Component, EventEmitter, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { FilterField, FilterOperator, FilterRow } from '../../models/search.model';
export type { FilterField, FilterOperator, FilterRow } from '../../models/search.model';

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
    <div class="dv-card dv-card--r10 fb">
      @for (row of rows(); track $index; let i = $index) {
        <div class="fb__row">
          <span class="fb__join">{{ i === 0 ? 'where' : 'and' }}</span>

          <!-- Field -->
          <span class="dv-pill fb__pill">
            <select
              class="fb__select"
              [attr.aria-label]="'Filter ' + (i + 1) + ' field'"
              [ngModel]="row.field"
              (ngModelChange)="onFieldChange(i, $event)"
            >
              @for (f of fields; track f.value) {
                <option [value]="f.value">{{ f.label }}</option>
              }
            </select>
            <span class="fb__caret" aria-hidden="true">▾</span>
          </span>

          <!-- Operator -->
          <span class="dv-pill dv-pill--op fb__pill">
            <select
              class="fb__select"
              [attr.aria-label]="'Filter ' + (i + 1) + ' operator'"
              [ngModel]="row.operator"
              (ngModelChange)="onOperatorChange(i, $event)"
            >
              @for (op of operatorsFor(row.field); track op.value) {
                <option [value]="op.value">{{ op.label }}</option>
              }
            </select>
            <span class="fb__caret" aria-hidden="true">▾</span>
          </span>

          <!-- Value -->
          @if (isDateField(row.field)) {
            <input
              type="date"
              class="dv-pill dv-pill--value fb__value"
              [attr.aria-label]="'Filter ' + (i + 1) + ' value'"
              [ngModel]="row.value"
              (ngModelChange)="onValueChange(i, $event)"
            />
          } @else {
            <input
              type="text"
              class="dv-pill dv-pill--value fb__value"
              placeholder="value…"
              [attr.aria-label]="'Filter ' + (i + 1) + ' value'"
              [ngModel]="row.value"
              (ngModelChange)="onValueChange(i, $event)"
              (keyup.enter)="emitFilters()"
            />
          }

          <button
            type="button"
            class="fb__x"
            title="Remove filter"
            aria-label="Remove filter"
            (click)="removeRow(i)"
          >
            ✕
          </button>
        </div>
      }

      <div class="fb__foot">
        <button type="button" class="fb__action" (click)="addRow()">
          + {{ rows().length ? 'and' : 'where' }}
        </button>
        @if (rows().length) {
          <button type="button" class="fb__action" (click)="clearAll()">
            clear all
          </button>
          <button type="button" class="fb__action fb__action--accent" (click)="emitFilters()">
            apply ↵
          </button>
        } @else {
          <span class="fb__hint">no filters — every document is in scope</span>
        }
      </div>
    </div>
  `,
  styles: [
    `
      $mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

      :host {
        display: block;
      }

      .fb {
        padding: 12px 14px;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .fb__row {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        font: 400 12px #{$mono};
      }

      .fb__join {
        color: var(--faint);
        width: 34px;
        flex-shrink: 0;
      }

      .fb__pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }

      .fb__select {
        appearance: none;
        background: transparent;
        border: none;
        padding: 0;
        outline: none;
        color: inherit;
        font: inherit;
        cursor: pointer;

        option {
          background: var(--panel);
          color: var(--text);
        }
      }

      .fb__caret {
        color: var(--faint);
      }

      .fb__value {
        width: 190px;
        max-width: 100%;
        outline: none;
        cursor: text;

        &::placeholder {
          color: var(--faint);
        }
      }

      .fb__x {
        background: none;
        border: none;
        padding: 0 4px;
        color: var(--faint);
        font: inherit;
        cursor: pointer;

        &:hover {
          color: var(--danger);
        }
      }

      .fb__foot {
        display: flex;
        gap: 14px;
        align-items: center;
        padding-left: 42px;
        font: 400 12px #{$mono};
      }

      .fb__action {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        color: var(--faint);
        cursor: pointer;

        &:hover {
          color: var(--text);
        }

        &--accent {
          margin-left: auto;
          color: var(--accent-text);

          &:hover {
            color: var(--text);
          }
        }
      }

      .fb__hint {
        color: var(--faint);
      }
    `,
  ],
})
export class SearchFilterBuilderComponent {
  @Output() filtersChange = new EventEmitter<FilterRow[]>();

  rows = signal<FilterRow[]>([]);

  readonly fields = FILTER_FIELDS;
  readonly allOperators = FILTER_OPERATORS;

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
