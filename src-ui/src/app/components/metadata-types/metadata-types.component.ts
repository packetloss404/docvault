import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrganizationService } from '../../services/organization.service';
import { MetadataType } from '../../models/organization.model';

@Component({
  selector: 'app-metadata-types',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './metadata-types.component.html',
})
export class MetadataTypesComponent implements OnInit {
  metadataTypes = signal<MetadataType[]>([]);
  editing = signal<MetadataType | null>(null);
  creating = signal(false);

  editName = signal('');
  editLabel = signal('');
  editDefault = signal('');
  editLookup = signal('');
  editValidation = signal('');
  editParser = signal('');

  builtinValidators = ['required', 'regex', 'numeric_range', 'date_format'];
  builtinParsers = ['integer', 'float', 'date'];

  constructor(private orgService: OrganizationService) {}

  ngOnInit(): void {
    this.loadTypes();
  }

  loadTypes(): void {
    this.orgService.getMetadataTypes().subscribe({
      next: (res) => this.metadataTypes.set(res.results),
    });
  }

  startCreate(): void {
    this.creating.set(true);
    this.editing.set(null);
    this.editName.set('');
    this.editLabel.set('');
    this.editDefault.set('');
    this.editLookup.set('');
    this.editValidation.set('');
    this.editParser.set('');
  }

  startEdit(mt: MetadataType): void {
    this.editing.set(mt);
    this.creating.set(false);
    this.editName.set(mt.name);
    this.editLabel.set(mt.label);
    this.editDefault.set(mt.default);
    this.editLookup.set(mt.lookup);
    this.editValidation.set(mt.validation);
    this.editParser.set(mt.parser);
  }

  cancelEdit(): void {
    this.editing.set(null);
    this.creating.set(false);
  }

  save(): void {
    const data: Partial<MetadataType> = {
      name: this.editName(),
      label: this.editLabel(),
      default: this.editDefault(),
      lookup: this.editLookup(),
      validation: this.editValidation(),
      parser: this.editParser(),
    };

    if (this.creating()) {
      this.orgService.createMetadataType(data).subscribe({
        next: () => {
          this.cancelEdit();
          this.loadTypes();
        },
      });
    } else if (this.editing()) {
      this.orgService.updateMetadataType(this.editing()!.id, data).subscribe({
        next: () => {
          this.cancelEdit();
          this.loadTypes();
        },
      });
    }
  }

  deleteType(mt: MetadataType): void {
    if (!confirm(`Delete metadata type "${mt.name}"?`)) return;
    this.orgService.deleteMetadataType(mt.id).subscribe({
      next: () => this.loadTypes(),
    });
  }
}
