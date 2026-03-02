import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { DocumentService } from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';
import { Document, DocumentType, DocumentVersion } from '../../models/document.model';
import {
  AutocompleteItem,
  CustomField,
  CustomFieldInstance,
  DocumentMetadata,
  MetadataType,
  Tag,
} from '../../models/organization.model';
import { WorkflowPanelComponent } from '../workflow-panel/workflow-panel.component';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, WorkflowPanelComponent],
  templateUrl: './document-detail.component.html',
})
export class DocumentDetailComponent implements OnInit {
  document = signal<Document | null>(null);
  documentTypes = signal<DocumentType[]>([]);
  versions = signal<DocumentVersion[]>([]);
  activeTab = signal<'details' | 'content' | 'preview' | 'metadata' | 'workflows'>('details');
  editing = signal(false);
  loading = signal(true);

  allTags = signal<Tag[]>([]);
  allCorrespondents = signal<AutocompleteItem[]>([]);
  allCabinets = signal<AutocompleteItem[]>([]);

  // Custom fields & metadata
  customFieldInstances = signal<CustomFieldInstance[]>([]);
  allCustomFields = signal<CustomField[]>([]);
  documentMetadata = signal<DocumentMetadata[]>([]);
  allMetadataTypes = signal<MetadataType[]>([]);

  // Add custom field form
  addFieldId = signal<number | null>(null);
  addFieldValue = signal<string>('');
  addMetadataTypeId = signal<number | null>(null);
  addMetadataValue = signal<string>('');

  // Edit form fields
  editTitle = signal('');
  editDocumentType = signal<number | null>(null);
  editCorrespondent = signal<number | null>(null);
  editCabinet = signal<number | null>(null);
  editLanguage = signal('');
  editAsn = signal<number | null>(null);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private documentService: DocumentService,
    private orgService: OrganizationService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.loadDocument(id);
      this.loadVersions(id);
      this.loadCustomFields(id);
      this.loadDocumentMetadata(id);
    }
    this.loadDocumentTypes();
    this.loadOrganization();
    this.loadAllCustomFields();
    this.loadAllMetadataTypes();
  }

  loadOrganization(): void {
    this.orgService.getTags().subscribe({
      next: (res) => this.allTags.set(res.results),
    });
    this.orgService.autocompleteCorrespondent('').subscribe({
      next: (items) => this.allCorrespondents.set(items),
    });
    this.orgService.autocompleteCabinet('').subscribe({
      next: (items) => this.allCabinets.set(items),
    });
  }

  loadDocument(id: number): void {
    this.loading.set(true);
    this.documentService.getDocument(id).subscribe({
      next: (doc) => {
        this.document.set(doc);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.router.navigate(['/documents']);
      },
    });
  }

  loadVersions(id: number): void {
    this.documentService.getVersions(id).subscribe({
      next: (versions) => this.versions.set(versions),
    });
  }

  loadDocumentTypes(): void {
    this.documentService.getDocumentTypes().subscribe({
      next: (response) => this.documentTypes.set(response.results),
    });
  }

  setTab(tab: 'details' | 'content' | 'preview' | 'metadata' | 'workflows'): void {
    this.activeTab.set(tab);
  }

  startEdit(): void {
    const doc = this.document();
    if (!doc) return;
    this.editTitle.set(doc.title);
    this.editDocumentType.set(doc.document_type);
    this.editCorrespondent.set(doc.correspondent);
    this.editCabinet.set(doc.cabinet);
    this.editLanguage.set(doc.language);
    this.editAsn.set(doc.archive_serial_number);
    this.editing.set(true);
  }

  cancelEdit(): void {
    this.editing.set(false);
  }

  saveEdit(): void {
    const doc = this.document();
    if (!doc) return;

    this.documentService
      .updateDocument(doc.id, {
        title: this.editTitle(),
        document_type: this.editDocumentType(),
        correspondent: this.editCorrespondent(),
        cabinet: this.editCabinet(),
        language: this.editLanguage(),
        archive_serial_number: this.editAsn(),
      } as Partial<Document>)
      .subscribe({
        next: (updated) => {
          this.document.set(updated);
          this.editing.set(false);
        },
      });
  }

  deleteDocument(): void {
    const doc = this.document();
    if (!doc) return;
    if (!confirm(`Delete "${doc.title}"? It will be moved to trash.`)) return;

    this.documentService.deleteDocument(doc.id).subscribe({
      next: () => this.router.navigate(['/documents']),
    });
  }

  getPreviewUrl(): string {
    const doc = this.document();
    return doc ? this.documentService.getPreviewUrl(doc.id) : '';
  }

  getDownloadUrl(version: 'original' | 'archive' = 'original'): string {
    const doc = this.document();
    return doc ? this.documentService.getDownloadUrl(doc.id, version) : '';
  }

  activateVersion(versionId: number): void {
    const doc = this.document();
    if (!doc) return;
    this.documentService.activateVersion(doc.id, versionId).subscribe({
      next: () => this.loadVersions(doc.id),
    });
  }

  // --- Custom Fields & Metadata ---

  loadCustomFields(docId: number): void {
    this.orgService.getDocumentCustomFields(docId).subscribe({
      next: (instances) => this.customFieldInstances.set(instances),
    });
  }

  loadDocumentMetadata(docId: number): void {
    this.orgService.getDocumentMetadata(docId).subscribe({
      next: (metadata) => this.documentMetadata.set(metadata),
    });
  }

  loadAllCustomFields(): void {
    this.orgService.getCustomFields().subscribe({
      next: (res) => this.allCustomFields.set(res.results),
    });
  }

  loadAllMetadataTypes(): void {
    this.orgService.getMetadataTypes().subscribe({
      next: (res) => this.allMetadataTypes.set(res.results),
    });
  }

  addCustomField(): void {
    const doc = this.document();
    const fieldId = this.addFieldId();
    if (!doc || !fieldId) return;

    let parsedValue: unknown = this.addFieldValue();
    const field = this.allCustomFields().find((f) => f.id === fieldId);
    if (field) {
      if (field.data_type === 'integer') parsedValue = parseInt(this.addFieldValue(), 10);
      else if (field.data_type === 'float' || field.data_type === 'monetary')
        parsedValue = parseFloat(this.addFieldValue());
      else if (field.data_type === 'boolean') parsedValue = this.addFieldValue() === 'true';
    }

    this.orgService.setDocumentCustomField(doc.id, fieldId, parsedValue).subscribe({
      next: () => {
        this.addFieldId.set(null);
        this.addFieldValue.set('');
        this.loadCustomFields(doc.id);
      },
    });
  }

  removeCustomField(instanceId: number): void {
    const doc = this.document();
    if (!doc) return;
    this.orgService.deleteDocumentCustomField(doc.id, instanceId).subscribe({
      next: () => this.loadCustomFields(doc.id),
    });
  }

  addMetadata(): void {
    const doc = this.document();
    const mtId = this.addMetadataTypeId();
    if (!doc || !mtId) return;

    this.orgService.setDocumentMetadata(doc.id, mtId, this.addMetadataValue()).subscribe({
      next: () => {
        this.addMetadataTypeId.set(null);
        this.addMetadataValue.set('');
        this.loadDocumentMetadata(doc.id);
      },
    });
  }

  removeMetadata(instanceId: number): void {
    const doc = this.document();
    if (!doc) return;
    this.orgService.deleteDocumentMetadata(doc.id, instanceId).subscribe({
      next: () => this.loadDocumentMetadata(doc.id),
    });
  }

  formatFileSize(bytes: number): string {
    if (!bytes) return 'Unknown';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
  }
}
