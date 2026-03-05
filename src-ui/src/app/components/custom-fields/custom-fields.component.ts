import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { CustomField, CustomFieldDataType } from '../../models/organization.model';

@Component({
  selector: 'app-custom-fields',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './custom-fields.component.html',
})
export class CustomFieldsComponent implements OnInit {
  fields = signal<CustomField[]>([]);
  editing = signal<CustomField | null>(null);
  creating = signal(false);

  editName = signal('');
  editDataType = signal<CustomFieldDataType>('string');
  editSelectOptions = signal('');

  dataTypes: { value: CustomFieldDataType; label: string }[] = [
    { value: 'string', label: 'String' },
    { value: 'longtext', label: 'Long Text' },
    { value: 'url', label: 'URL' },
    { value: 'date', label: 'Date' },
    { value: 'datetime', label: 'Date & Time' },
    { value: 'boolean', label: 'Boolean' },
    { value: 'integer', label: 'Integer' },
    { value: 'float', label: 'Float' },
    { value: 'monetary', label: 'Monetary' },
    { value: 'documentlink', label: 'Document Link' },
    { value: 'select', label: 'Select' },
    { value: 'multiselect', label: 'Multi-Select' },
  ];

  constructor(private orgService: OrganizationService) {}

  ngOnInit(): void {
    this.loadFields();
  }

  loadFields(): void {
    this.orgService.getCustomFields().subscribe({
      next: (res) => this.fields.set(res.results),
    });
  }

  startCreate(): void {
    this.creating.set(true);
    this.editing.set(null);
    this.editName.set('');
    this.editDataType.set('string');
    this.editSelectOptions.set('');
  }

  startEdit(field: CustomField): void {
    this.editing.set(field);
    this.creating.set(false);
    this.editName.set(field.name);
    this.editDataType.set(field.data_type);
    const opts = (field.extra_data?.['options'] as string[]) || [];
    this.editSelectOptions.set(opts.join('\n'));
  }

  cancelEdit(): void {
    this.editing.set(null);
    this.creating.set(false);
  }

  save(): void {
    const extra_data: Record<string, unknown> = {};
    const dt = this.editDataType();
    if (dt === 'select' || dt === 'multiselect') {
      extra_data['options'] = this.editSelectOptions()
        .split('\n')
        .map((o) => o.trim())
        .filter((o) => o.length > 0);
    }

    const data: Partial<CustomField> = {
      name: this.editName(),
      data_type: dt,
      extra_data,
    };

    if (this.creating()) {
      this.orgService.createCustomField(data).subscribe({
        next: () => {
          this.cancelEdit();
          this.loadFields();
        },
      });
    } else if (this.editing()) {
      this.orgService.updateCustomField(this.editing()!.id, data).subscribe({
        next: () => {
          this.cancelEdit();
          this.loadFields();
        },
      });
    }
  }

  deleteField(field: CustomField): void {
    if (!confirm(`Delete custom field "${field.name}"?`)) return;
    this.orgService.deleteCustomField(field.id).subscribe({
      next: () => this.loadFields(),
    });
  }

  isSelectType(): boolean {
    const dt = this.editDataType();
    return dt === 'select' || dt === 'multiselect';
  }
}
