import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
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
import { SummaryResponse, EntityResponse, TitleSuggestion } from '../../models/ai.model';
import { ActivityEntry, CheckoutStatus, ShareLink } from '../../models/collaboration.model';
import { Annotation } from '../../models/annotation.model';
import { AnnotationService } from '../../services/annotation.service';
import { AnnotationToolSelection } from '../annotation-toolbar/annotation-toolbar.component';
import { WorkflowPanelComponent } from '../workflow-panel/workflow-panel.component';
import { CommentsComponent } from '../comments/comments.component';
import { DocumentSignaturesComponent } from '../document-signatures/document-signatures.component';
import { SuggestionPanelComponent } from '../suggestion-panel/suggestion-panel.component';
import { RelationshipPanelComponent } from '../relationship-panel/relationship-panel.component';
import { DocumentChatComponent } from '../document-chat/document-chat.component';
import { SimilarDocumentsComponent } from '../similar-documents/similar-documents.component';
import { AnnotationToolbarComponent } from '../annotation-toolbar/annotation-toolbar.component';
import { AnnotationPanelComponent } from '../annotation-panel/annotation-panel.component';
import { IconComponent } from '../icon/icon.component';
import { AIService } from '../../services/ai.service';
import { EsignatureService } from '../../services/esignature.service';
import { ZoneOCRService } from '../../services/zone-ocr.service';
import { PhysicalRecordService } from '../../services/physical-record.service';

/**
 * Right-pane tab keys. `preview` is no longer a tab — the preview lives
 * permanently in the left pane of the split view — and the old `ai` tab is now
 * `ask`; `setTab` still accepts both legacy names.
 */
export type DocumentDetailTab =
  | 'details'
  | 'activity'
  | 'notes'
  | 'ask'
  | 'versions'
  | 'related'
  | 'content'
  | 'metadata'
  | 'workflows'
  | 'signatures'
  | 'zone-ocr'
  | 'physical';

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
    IconComponent,
  ],
  templateUrl: './document-detail.component.html',
  styleUrl: './document-detail.component.scss',
})
export class DocumentDetailComponent implements OnInit {
  document = signal<Document | null>(null);
  documentTypes = signal<DocumentType[]>([]);
  versions = signal<DocumentVersion[]>([]);
  activeTab = signal<DocumentDetailTab>('details');
  editing = signal(false);
  loading = signal(true);

  /** Tab strip, in order. The strip scrolls horizontally inside the 400px pane. */
  readonly tabs: ReadonlyArray<{ key: DocumentDetailTab; label: string }> = [
    { key: 'details', label: 'Details' },
    { key: 'activity', label: 'Activity' },
    { key: 'notes', label: 'Notes' },
    { key: 'ask', label: 'Ask AI' },
    { key: 'versions', label: 'Versions' },
    { key: 'related', label: 'Related' },
    { key: 'content', label: 'Content' },
    { key: 'metadata', label: 'Metadata' },
    { key: 'workflows', label: 'Workflows' },
    { key: 'signatures', label: 'Signatures' },
    { key: 'zone-ocr', label: 'Zone OCR' },
    { key: 'physical', label: 'Physical' },
  ];

  // Legal hold
  isHeld = signal(false);

  // Collaboration
  checkoutStatus = signal<CheckoutStatus | null>(null);
  shareLinks = signal<ShareLink[]>([]);
  newShareExpHours = signal<number | null>(24);
  newSharePassword = signal('');
  isCheckedOut = computed(() => this.checkoutStatus()?.checked_out === true);

  // Activity timeline (loaded lazily when the Activity tab is first opened)
  activityEntries = signal<ActivityEntry[]>([]);
  activityLoading = signal(false);
  activityError = signal(false);
  private activityRequested = false;

  // Left pane: viewer state
  zoom = signal(100);
  currentPage = signal(1);
  thumbFailed = signal(false);
  pageCount = computed(() => Math.max(1, this.document()?.page_count ?? 1));

  // Annotations shown as overlays on the rendered page layer
  annotations = signal<Annotation[]>([]);
  annotationsVisible = signal(true);
  annotationAuthorFilter = signal('');
  activeAnnotationTool = signal<AnnotationToolSelection | null>(null);

  // Tag editing (uses the bulk endpoint — document tags are read-only on PATCH)
  showTagPicker = signal(false);
  tagBusy = signal(false);
  actionMessage = signal('');
  actionError = signal(false);

  // AI / Signatures / Zone OCR / Physical signals
  aiHealthy = signal(true);
  signatureRequests = signal<any[]>([]);
  zoneOcrTemplates = signal<any[]>([]);
  zoneOcrResults = signal<any[]>([]);
  selectedOcrTemplate = signal<number | null>(null);
  physicalRecord = signal<any>(null);

  // AI stretch-action signals
  aiSummary = signal<SummaryResponse | null>(null);
  aiSummaryLoading = signal(false);
  aiEntities = signal<EntityResponse | null>(null);
  aiEntitiesLoading = signal(false);
  aiSuggestedTitle = signal<TitleSuggestion | null>(null);
  aiSuggestedTitleLoading = signal(false);

  // Content-tab in-text search
  contentSearchQuery = signal('');
  highlightedContent = computed(() => {
    const doc = this.document();
    const content = doc?.content ?? '';
    const query = this.contentSearchQuery().trim();
    if (!query) return this.escapeHtml(content);
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    return this.escapeHtml(content).replace(regex, '<mark>$1</mark>');
  });

  allTags = signal<Tag[]>([]);
  allCorrespondents = signal<AutocompleteItem[]>([]);
  allCabinets = signal<AutocompleteItem[]>([]);

  /** Tags currently on the document, resolved against the tag list. */
  documentTags = computed<Tag[]>(() => {
    const ids = this.document()?.tag_ids ?? [];
    return this.allTags().filter((tag) => ids.includes(tag.id));
  });

  /** Tags that could still be added. */
  assignableTags = computed<Tag[]>(() => {
    const ids = this.document()?.tag_ids ?? [];
    return this.allTags().filter((tag) => !ids.includes(tag.id));
  });

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
    private annotationService: AnnotationService,
    private sanitizer: DomSanitizer,
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
      this.loadAnnotations(id);
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
        this.thumbFailed.set(false);
        this.currentPage.set(Math.min(this.currentPage(), Math.max(1, doc.page_count || 1)));
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

  /**
   * Switch the right-pane tab. `preview` and `ai` are accepted as legacy
   * aliases: the preview is now permanent in the left pane, and the old AI tab
   * became `ask`.
   */
  setTab(tab: DocumentDetailTab | 'preview' | 'ai'): void {
    const next: DocumentDetailTab =
      tab === 'ai' ? 'ask' : tab === 'preview' ? 'details' : tab;
    this.activeTab.set(next);
    if (next === 'activity') this.ensureActivityLoaded();
  }

  // --- Activity timeline ---

  ensureActivityLoaded(): void {
    if (this.activityRequested) return;
    const id = this.document()?.id ?? Number(this.route.snapshot.paramMap.get('id'));
    if (!id) return;
    this.activityRequested = true;
    this.loadActivity(id);
  }

  loadActivity(docId: number): void {
    this.activityLoading.set(true);
    this.activityError.set(false);
    this.collaborationService.getDocumentActivity(docId).subscribe({
      next: (entries) => {
        this.activityEntries.set(entries);
        this.activityLoading.set(false);
      },
      error: () => {
        this.activityEntries.set([]);
        this.activityError.set(true);
        this.activityLoading.set(false);
      },
    });
  }

  /** Timeline dot colour by event kind. */
  activityDotClass(eventType: string): string {
    const type = (eventType || '').toLowerCase();
    if (type.includes('failed') || type.includes('error')) return 'dv-dot--danger';
    if (type.includes('warning') || type.includes('retention') || type.includes('quota'))
      return 'dv-dot--warn';
    if (type.includes('processed') || type.includes('completed')) return 'dv-dot--ok';
    if (
      type.includes('comment') ||
      type.includes('share') ||
      type.includes('workflow') ||
      type.includes('transition')
    )
      return 'dv-dot--accent';
    return '';
  }

  formatEventType(eventType: string): string {
    return (eventType || '').replace(/_/g, ' ');
  }

  /** Short mono timestamp for timeline rows: "3h ago", "12d ago", or a date. */
  formatRelative(iso: string | null | undefined): string {
    if (!iso) return '';
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return '';
    const seconds = Math.floor((Date.now() - then) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return new Date(iso).toISOString().slice(0, 10);
  }

  // --- Left pane viewer ---

  /** Which preview surface the left pane can actually render. */
  previewKind = computed<'pdf' | 'image' | 'thumb' | 'none'>(() => {
    const doc = this.document();
    if (!doc) return 'none';
    if (doc.mime_type === 'application/pdf' || doc.archive_filename) return 'pdf';
    if (doc.mime_type?.startsWith('image/')) return 'image';
    if (doc.thumbnail_path && !this.thumbFailed()) return 'thumb';
    return 'none';
  });

  /**
   * PDF viewer URL. The page and zoom fragment is a standard PDF open
   * parameter, so the toolbar controls drive the embedded viewer for real.
   */
  previewFrameUrl = computed<SafeResourceUrl>(() => {
    const doc = this.document();
    if (!doc) return this.sanitizer.bypassSecurityTrustResourceUrl('about:blank');
    const base = this.documentService.getDownloadUrl(
      doc.id,
      doc.archive_filename ? 'archive' : 'original',
    );
    return this.sanitizer.bypassSecurityTrustResourceUrl(
      `${base}#page=${this.currentPage()}&zoom=${this.zoom()}`,
    );
  });

  zoomIn(): void {
    this.zoom.set(Math.min(200, this.zoom() + 25));
  }

  zoomOut(): void {
    this.zoom.set(Math.max(50, this.zoom() - 25));
  }

  resetZoom(): void {
    this.zoom.set(100);
  }

  prevPage(): void {
    this.currentPage.set(Math.max(1, this.currentPage() - 1));
  }

  nextPage(): void {
    this.currentPage.set(Math.min(this.pageCount(), this.currentPage() + 1));
  }

  // --- Annotations (left pane overlay + Notes tab list) ---

  loadAnnotations(docId: number): void {
    this.annotationService.getAnnotations(docId).subscribe({
      next: (items) => this.annotations.set(items),
      error: () => this.annotations.set([]),
    });
  }

  /** Annotations on the page currently shown, honouring toolbar filters. */
  pageAnnotations = computed<Annotation[]>(() => {
    if (!this.annotationsVisible()) return [];
    const page = this.currentPage();
    const author = this.annotationAuthorFilter().trim().toLowerCase();
    return this.annotations().filter(
      (a) =>
        a.page === page &&
        (!author || (a.author_name ?? '').toLowerCase().includes(author)),
    );
  });

  /**
   * Overlay boxes. Coordinates are normalised 0–1 server-side; anything without
   * a usable box is left out rather than guessed at.
   */
  overlayBoxes = computed<Annotation[]>(() =>
    this.pageAnnotations().filter(
      (a) =>
        ['highlight', 'underline', 'strikethrough', 'rectangle'].includes(
          a.annotation_type,
        ) &&
        this.isFraction(a.coordinates?.['x']) &&
        this.isFraction(a.coordinates?.['y']) &&
        this.isFraction(a.coordinates?.['width']) &&
        this.isFraction(a.coordinates?.['height']),
    ),
  );

  /** Sticky notes / text boxes with a point anchor and something to say. */
  overlayNotes = computed<Annotation[]>(() =>
    this.pageAnnotations().filter(
      (a) =>
        ['sticky_note', 'text_box', 'rubber_stamp'].includes(a.annotation_type) &&
        !!a.content &&
        this.isFraction(a.coordinates?.['x']) &&
        this.isFraction(a.coordinates?.['y']),
    ),
  );

  coord(annotation: Annotation, key: string): number {
    const value = annotation.coordinates?.[key];
    return typeof value === 'number' ? value * 100 : 0;
  }

  onAnnotationTool(selection: AnnotationToolSelection): void {
    this.activeAnnotationTool.set(selection);
  }

  onAnnotationVisibility(visible: boolean): void {
    this.annotationsVisible.set(visible);
  }

  onAnnotationAuthorFilter(author: string): void {
    this.annotationAuthorFilter.set(author);
  }

  onAnnotationSelected(annotation: Annotation): void {
    if (annotation.page) this.currentPage.set(annotation.page);
  }

  annotationAuthors = computed<string[]>(() => {
    const names = new Set<string>();
    for (const a of this.annotations()) {
      if (a.author_name) names.add(a.author_name);
    }
    return [...names];
  });

  // --- Tags ---

  /**
   * Tags are read-only on the document serializer, so add/remove go through the
   * bulk endpoint. A document under legal hold returns HTTP 409 there.
   */
  addTag(tagId: number | null): void {
    const doc = this.document();
    if (!doc || !tagId) return;
    this.tagBusy.set(true);
    this.documentService
      .bulkOperation({ action: 'add_tags', document_ids: [doc.id], tag_ids: [tagId] })
      .subscribe({
        next: () => {
          this.tagBusy.set(false);
          this.showTagPicker.set(false);
          this.setActionMessage('Tag added.', false);
          this.loadDocument(doc.id);
        },
        error: (err) => {
          this.tagBusy.set(false);
          this.setActionMessage(this.mutationError(err, 'Could not add the tag.'), true);
        },
      });
  }

  removeTag(tagId: number): void {
    const doc = this.document();
    if (!doc) return;
    this.tagBusy.set(true);
    this.documentService
      .bulkOperation({ action: 'remove_tags', document_ids: [doc.id], tag_ids: [tagId] })
      .subscribe({
        next: () => {
          this.tagBusy.set(false);
          this.setActionMessage('Tag removed.', false);
          this.loadDocument(doc.id);
        },
        error: (err) => {
          this.tagBusy.set(false);
          this.setActionMessage(this.mutationError(err, 'Could not remove the tag.'), true);
        },
      });
  }

  private setActionMessage(message: string, isError: boolean): void {
    this.actionMessage.set(message);
    this.actionError.set(isError);
  }

  clearActionMessage(): void {
    this.actionMessage.set('');
    this.actionError.set(false);
  }

  private mutationError(err: unknown, fallback: string): string {
    const status = (err as { status?: number })?.status;
    if (status === 409) {
      return 'Blocked — this document is under legal hold (HTTP 409).';
    }
    return fallback;
  }

  private isFraction(value: unknown): boolean {
    return typeof value === 'number' && value >= 0 && value <= 1;
  }

  /** Status chip modifier for a signature request. */
  signatureChipClass(status: string): string {
    const value = (status || '').toLowerCase();
    if (value === 'completed' || value === 'signed') return 'dv-chip--ok';
    if (value === 'pending' || value === 'sent') return 'dv-chip--warn';
    if (value === 'declined' || value === 'cancelled' || value === 'expired')
      return 'dv-chip--danger';
    return '';
  }

  /** The two newest versions, used for the side-by-side diff affordance. */
  diffPair = computed<DocumentVersion[]>(() => {
    const sorted = [...this.versions()].sort(
      (a, b) => b.version_number - a.version_number,
    );
    return sorted.slice(0, 2);
  });

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

  // --- AI stretch actions ---

  summarizeDocument(): void {
    const doc = this.document();
    if (!doc) return;
    this.aiSummaryLoading.set(true);
    this.aiSummary.set(null);
    this.aiService.summarize(doc.id).subscribe({
      next: (res) => {
        this.aiSummary.set(res);
        this.aiSummaryLoading.set(false);
      },
      error: () => {
        this.aiSummary.set({ summary: null, error: 'Failed to generate summary.' });
        this.aiSummaryLoading.set(false);
      },
    });
  }

  extractEntities(): void {
    const doc = this.document();
    if (!doc) return;
    this.aiEntitiesLoading.set(true);
    this.aiEntities.set(null);
    this.aiService.extractEntities(doc.id).subscribe({
      next: (res) => {
        this.aiEntities.set(res);
        this.aiEntitiesLoading.set(false);
      },
      error: () => {
        this.aiEntities.set({ entities: null, error: 'Failed to extract entities.' });
        this.aiEntitiesLoading.set(false);
      },
    });
  }

  suggestTitle(): void {
    const doc = this.document();
    if (!doc) return;
    this.aiSuggestedTitleLoading.set(true);
    this.aiSuggestedTitle.set(null);
    this.aiService.suggestTitle(doc.id).subscribe({
      next: (res) => {
        this.aiSuggestedTitle.set(res);
        this.aiSuggestedTitleLoading.set(false);
      },
      error: () => {
        this.aiSuggestedTitle.set({ suggested_title: null, error: 'Failed to suggest title.' });
        this.aiSuggestedTitleLoading.set(false);
      },
    });
  }

  aiEntitiesKeys(): string[] {
    const entities = this.aiEntities()?.entities;
    return entities ? Object.keys(entities) : [];
  }

  // --- Content search helper ---

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}
