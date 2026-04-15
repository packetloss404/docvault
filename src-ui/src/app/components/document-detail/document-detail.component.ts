import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { DocumentService } from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';
import { CollaborationService } from '../../services/collaboration.service';
import { LegalHoldService } from '../../services/legal-hold.service';
import { Document, DocumentType, DocumentVersion } from '../../models/document.model';
import {
  AutocompleteItem,
  CustomField,
  CustomFieldInstance,
  DocumentMetadata,
  MetadataType,
  Tag,
} from '../../models/organization.model';
import { CheckoutStatus, ShareLink } from '../../models/collaboration.model';
import { WorkflowPanelComponent } from '../workflow-panel/workflow-panel.component';
import { CommentsComponent } from '../comments/comments.component';
import { DocumentSignaturesComponent } from '../document-signatures/document-signatures.component';
import { SuggestionPanelComponent } from '../suggestion-panel/suggestion-panel.component';
import { RelationshipPanelComponent } from '../relationship-panel/relationship-panel.component';
import { DocumentChatComponent } from '../document-chat/document-chat.component';
import { SimilarDocumentsComponent } from '../similar-documents/similar-documents.component';
import { AnnotationToolbarComponent } from '../annotation-toolbar/annotation-toolbar.component';
import { AnnotationPanelComponent } from '../annotation-panel/annotation-panel.component';
import { AIService } from '../../services/ai.service';
import { EsignatureService } from '../../services/esignature.service';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import { PhysicalRecordService } from '../../services/physical-record.service';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    WorkflowPanelComponent,
    CommentsComponent,
    DocumentSignaturesComponent,
    SuggestionPanelComponent,
    RelationshipPanelComponent,
    DocumentChatComponent,
    SimilarDocumentsComponent,
    AnnotationToolbarComponent,
    AnnotationPanelComponent,
  ],
  templateUrl: './document-detail.component.html',
})
export class DocumentDetailComponent implements OnInit {
  document = signal<Document | null>(null);
  documentTypes = signal<DocumentType[]>([]);
  versions = signal<DocumentVersion[]>([]);
  activeTab = signal<'details' | 'content' | 'preview' | 'metadata' | 'workflows' | 'signatures' | 'ai' | 'zone-ocr' | 'physical'>('details');
  editing = signal(false);
  loading = signal(true);

  // Legal hold
  isHeld = signal(false);

  // Collaboration
  checkoutStatus = signal<CheckoutStatus | null>(null);
  shareLinks = signal<ShareLink[]>([]);
  newShareExpHours = signal<number | null>(24);
  newSharePassword = signal('');

  // AI / Signatures / Zone OCR / Physical signals
  aiHealthy = signal(true);
  signatureRequests = signal<any[]>([]);
  zoneOcrTemplates = signal<any[]>([]);
  zoneOcrResults = signal<any[]>([]);
  selectedOcrTemplate = signal<number | null>(null);
  physicalRecord = signal<any>(null);

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
    private collaborationService: CollaborationService,
    private legalHoldService: LegalHoldService,
    private aiService: AIService,
    private esignatureService: EsignatureService,
    private zoneOcrService: ZoneOCRService,
    private physicalRecordService: PhysicalRecordService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.loadDocument(id);
      this.loadVersions(id);
      this.loadCustomFields(id);
      this.loadDocumentMetadata(id);
      this.loadSignatureRequests(id);
      this.loadPhysicalRecord(id);
      this.loadLegalHoldStatus(id);
      this.loadCheckoutStatus(id);
      this.loadShareLinks(id);
    }
    this.loadDocumentTypes();
    this.loadOrganization();
    this.loadAllCustomFields();
    this.loadAllMetadataTypes();
    this.loadAiStatus();
    this.loadZoneOcrTemplates();
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

  setTab(tab: 'details' | 'content' | 'preview' | 'metadata' | 'workflows' | 'signatures' | 'ai' | 'zone-ocr' | 'physical'): void {
    this.activeTab.set(tab);
  }

  // --- AI ---

  loadAiStatus(): void {
    this.aiService.getStatus().subscribe({
      next: (status) => this.aiHealthy.set(status.llm_available),
      error: () => this.aiHealthy.set(false),
    });
  }

  // --- Signatures ---

  loadSignatureRequests(id: number): void {
    this.esignatureService.getRequests({ document: id.toString() }).subscribe({
      next: (requests) => this.signatureRequests.set(requests),
      error: () => this.signatureRequests.set([]),
    });
  }

  requestSignature(): void {
    const doc = this.document();
    if (!doc) return;
    this.esignatureService.createRequest(doc.id, { title: `Signature request for ${doc.title}` }).subscribe({
      next: () => this.loadSignatureRequests(doc.id),
    });
  }

  // --- Zone OCR ---

  loadZoneOcrTemplates(): void {
    this.zoneOcrService.getTemplates().subscribe({
      next: (res) => this.zoneOcrTemplates.set(res.results),
      error: () => this.zoneOcrTemplates.set([]),
    });
  }

  runZoneOcr(): void {
    const doc = this.document();
    const templateId = this.selectedOcrTemplate();
    if (!doc || !templateId) return;
    this.zoneOcrService.testTemplate(templateId, doc.id).subscribe({
      next: (results) => this.zoneOcrResults.set(results),
    });
  }

  // --- Physical Record ---

  loadPhysicalRecord(id: number): void {
    this.physicalRecordService.getRecords({ document: id.toString() }).subscribe({
      next: (res) => this.physicalRecord.set(res.results?.[0] ?? null),
      error: () => this.physicalRecord.set(null),
    });
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

  // --- Legal Hold ---

  loadLegalHoldStatus(docId: number): void {
    this.legalHoldService.getHolds({ document: String(docId) }).subscribe({
      next: (holds) => {
        this.isHeld.set(holds.some((h) => h.status === 'active'));
      },
      error: () => this.isHeld.set(false),
    });
  }

  // --- Collaboration ---

  loadCheckoutStatus(docId: number): void {
    this.collaborationService.getCheckoutStatus(docId).subscribe({
      next: (status) => this.checkoutStatus.set(status),
    });
  }

  loadShareLinks(docId: number): void {
    this.collaborationService.getShareLinks().subscribe({
      next: (links) => this.shareLinks.set(links.filter((l) => l.document === docId)),
    });
  }

  checkout(): void {
    const doc = this.document();
    if (!doc) return;
    this.collaborationService.checkout(doc.id).subscribe({
      next: () => this.loadCheckoutStatus(doc.id),
    });
  }

  checkin(): void {
    const doc = this.document();
    if (!doc) return;
    this.collaborationService.checkin(doc.id).subscribe({
      next: () => this.loadCheckoutStatus(doc.id),
    });
  }

  createShareLink(): void {
    const doc = this.document();
    if (!doc) return;
    const request: any = {};
    if (this.newShareExpHours()) request.expiration_hours = this.newShareExpHours();
    if (this.newSharePassword()) request.password = this.newSharePassword();
    this.collaborationService.createShareLink(doc.id, request).subscribe({
      next: () => {
        this.newShareExpHours.set(24);
        this.newSharePassword.set('');
        this.loadShareLinks(doc.id);
      },
    });
  }

  getShareUrl(link: ShareLink): string {
    return `${window.location.origin}/share/${link.slug}`;
  }

  copyShareUrl(link: ShareLink): void {
    navigator.clipboard.writeText(this.getShareUrl(link));
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
