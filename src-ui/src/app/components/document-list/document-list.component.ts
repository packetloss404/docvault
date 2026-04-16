import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  DocumentService,
  DocumentQueryParams,
} from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';
import {
  Document,
  DocumentType,
  PaginatedResponse,
} from '../../models/document.model';
import { Tag, Correspondent } from '../../models/organization.model';

const COLUMN_PREFS_KEY = 'dv_doc_list_columns';

export interface ColumnDef {
  key: string;
  label: string;
  sortable?: boolean;
  sortField?: string;
}

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './document-list.component.html',
})
export class DocumentListComponent implements OnInit {
  // --- Column configuration ---
  readonly availableColumns: ColumnDef[] = [
    { key: 'title', label: 'Title', sortable: true, sortField: 'title' },
    { key: 'document_type', label: 'Type' },
    { key: 'correspondent', label: 'Correspondent' },
    { key: 'cabinet', label: 'Cabinet' },
    { key: 'created', label: 'Created', sortable: true, sortField: 'created' },
    { key: 'added', label: 'Added', sortable: true, sortField: 'added' },
    { key: 'archive_serial_number', label: 'ASN' },
    { key: 'page_count', label: 'Pages' },
    { key: 'tags', label: 'Tags' },
  ];

  readonly defaultColumns = ['title', 'document_type', 'correspondent', 'created'];

  selectedColumns = signal<string[]>(this.defaultColumns);
  showColumnDropdown = signal(false);

  isColumnSelected(key: string): boolean {
    return this.selectedColumns().includes(key);
  }

  toggleColumn(key: string): void {
    const current = this.selectedColumns();
    if (current.includes(key)) {
      // Keep at least one column
      if (current.length <= 1) return;
      this.selectedColumns.set(current.filter((k) => k !== key));
    } else {
      // Maintain declaration order
      const ordered = this.availableColumns
        .map((c) => c.key)
        .filter((k) => [...current, key].includes(k));
      this.selectedColumns.set(ordered);
    }
    this.saveColumnPrefs();
  }

  loadColumnPrefs(): void {
    try {
      const stored = localStorage.getItem(COLUMN_PREFS_KEY);
      if (stored) {
        const parsed: string[] = JSON.parse(stored);
        const valid = parsed.filter((k) =>
          this.availableColumns.some((c) => c.key === k),
        );
        if (valid.length > 0) {
          this.selectedColumns.set(valid);
        }
      }
    } catch {
      // Ignore parse errors; use defaults
    }
  }

  saveColumnPrefs(): void {
    try {
      localStorage.setItem(
        COLUMN_PREFS_KEY,
        JSON.stringify(this.selectedColumns()),
      );
    } catch {
      // Ignore storage errors
    }
  }

  documents = signal<Document[]>([]);
  documentTypes = signal<DocumentType[]>([]);
  totalCount = signal(0);
  loading = signal(false);

  // Query state
  currentPage = signal(1);
  pageSize = signal(25);
  searchQuery = signal('');
  selectedTypeId = signal<number | null>(null);
  ordering = signal('-created');

  totalPages = computed(() => Math.ceil(this.totalCount() / this.pageSize()));

  // Bulk selection state
  selectedIds = signal<Set<number>>(new Set());
  hasSelection = computed(() => this.selectedIds().size > 0);
  selectionCount = computed(() => this.selectedIds().size);
  allSelected = computed(() => {
    const docs = this.documents();
    const sel = this.selectedIds();
    return docs.length > 0 && docs.every((d) => sel.has(d.id));
  });

  // Bulk action state
  bulkAction = signal<string | null>(null);
  bulkLoading = signal(false);
  bulkMessage = signal('');
  bulkError = signal(false);

  // Organization data for bulk actions
  tags = signal<Tag[]>([]);
  correspondents = signal<Correspondent[]>([]);

  // Bulk action form state
  selectedTagIds = signal<Set<number>>(new Set());
  selectedCorrespondentId = signal<number | null>(null);
  selectedDocTypeId = signal<number | null>(null);
  showDeleteConfirm = signal(false);

  constructor(
    private documentService: DocumentService,
    private organizationService: OrganizationService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.loadColumnPrefs();
    this.loadDocumentTypes();
    this.loadDocuments();
  }

  loadDocuments(): void {
    this.loading.set(true);
    const params: DocumentQueryParams = {
      page: this.currentPage(),
      page_size: this.pageSize(),
      ordering: this.ordering(),
    };
    if (this.searchQuery()) {
      params.search = this.searchQuery();
    }
    if (this.selectedTypeId()) {
      params.document_type = this.selectedTypeId()!;
    }

    this.documentService.getDocuments(params).subscribe({
      next: (response: PaginatedResponse<Document>) => {
        this.documents.set(response.results);
        this.totalCount.set(response.count);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  loadDocumentTypes(): void {
    this.documentService.getDocumentTypes().subscribe({
      next: (response) => this.documentTypes.set(response.results),
    });
  }

  onSearch(): void {
    this.currentPage.set(1);
    this.clearSelection();
    this.loadDocuments();
  }

  onTypeFilter(typeId: string): void {
    this.selectedTypeId.set(typeId ? Number(typeId) : null);
    this.currentPage.set(1);
    this.clearSelection();
    this.loadDocuments();
  }

  sortBy(field: string): void {
    const current = this.ordering();
    if (current === field) {
      this.ordering.set(`-${field}`);
    } else if (current === `-${field}`) {
      this.ordering.set(field);
    } else {
      this.ordering.set(field);
    }
    this.loadDocuments();
  }

  getSortIcon(field: string): string {
    const current = this.ordering();
    if (current === field) return 'bi-sort-up';
    if (current === `-${field}`) return 'bi-sort-down';
    return 'bi-chevron-expand';
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadDocuments();
  }

  openDocument(doc: Document): void {
    this.router.navigate(['/documents', doc.id]);
  }

  getPreviewUrl(doc: Document): string {
    return this.documentService.getPreviewUrl(doc.id);
  }

  // --- Selection ---

  toggleSelectAll(): void {
    const docs = this.documents();
    if (this.allSelected()) {
      this.selectedIds.set(new Set());
    } else {
      this.selectedIds.set(new Set(docs.map((d) => d.id)));
    }
  }

  toggleSelect(docId: number, event: Event): void {
    event.stopPropagation();
    const current = new Set(this.selectedIds());
    if (current.has(docId)) {
      current.delete(docId);
    } else {
      current.add(docId);
    }
    this.selectedIds.set(current);
  }

  isSelected(docId: number): boolean {
    return this.selectedIds().has(docId);
  }

  clearSelection(): void {
    this.selectedIds.set(new Set());
    this.bulkAction.set(null);
    this.showDeleteConfirm.set(false);
    this.bulkMessage.set('');
  }

  // --- Bulk Actions ---

  openBulkAction(action: string): void {
    this.bulkAction.set(action);
    this.bulkMessage.set('');
    this.bulkError.set(false);
    this.showDeleteConfirm.set(false);
    this.selectedTagIds.set(new Set());
    this.selectedCorrespondentId.set(null);
    this.selectedDocTypeId.set(null);

    if (action === 'add_tags') {
      this.loadTags();
    } else if (action === 'set_correspondent') {
      this.loadCorrespondents();
    } else if (action === 'set_type') {
      // documentTypes already loaded
    } else if (action === 'delete') {
      this.showDeleteConfirm.set(true);
    }
  }

  cancelBulkAction(): void {
    this.bulkAction.set(null);
    this.showDeleteConfirm.set(false);
    this.bulkMessage.set('');
  }

  private loadTags(): void {
    this.organizationService.getTags().subscribe({
      next: (res) => this.tags.set(res.results),
    });
  }

  private loadCorrespondents(): void {
    this.organizationService.getCorrespondents().subscribe({
      next: (res) => this.correspondents.set(res.results),
    });
  }

  toggleBulkTag(tagId: number): void {
    const current = new Set(this.selectedTagIds());
    if (current.has(tagId)) {
      current.delete(tagId);
    } else {
      current.add(tagId);
    }
    this.selectedTagIds.set(current);
  }

  isBulkTagSelected(tagId: number): boolean {
    return this.selectedTagIds().has(tagId);
  }

  executeBulkAddTags(): void {
    const tagIds = Array.from(this.selectedTagIds());
    if (tagIds.length === 0) return;
    this.bulkLoading.set(true);
    this.documentService
      .bulkOperation({
        action: 'add_tags',
        document_ids: Array.from(this.selectedIds()),
        tag_ids: tagIds,
      })
      .subscribe({
        next: (res) => {
          this.onBulkSuccess(`Tags added to ${res.affected} document(s).`);
        },
        error: () => this.onBulkError('Failed to add tags.'),
      });
  }

  executeBulkSetCorrespondent(): void {
    const corrId = this.selectedCorrespondentId();
    if (corrId === null) return;
    this.bulkLoading.set(true);
    this.documentService
      .bulkOperation({
        action: 'set_correspondent',
        document_ids: Array.from(this.selectedIds()),
        correspondent_id: corrId,
      })
      .subscribe({
        next: (res) => {
          this.onBulkSuccess(
            `Correspondent set on ${res.affected} document(s).`,
          );
        },
        error: () => this.onBulkError('Failed to set correspondent.'),
      });
  }

  executeBulkSetType(): void {
    const typeId = this.selectedDocTypeId();
    if (typeId === null) return;
    this.bulkLoading.set(true);
    this.documentService
      .bulkOperation({
        action: 'set_document_type',
        document_ids: Array.from(this.selectedIds()),
        document_type_id: typeId,
      })
      .subscribe({
        next: (res) => {
          this.onBulkSuccess(
            `Document type set on ${res.affected} document(s).`,
          );
        },
        error: () => this.onBulkError('Failed to set document type.'),
      });
  }

  executeBulkDelete(): void {
    this.bulkLoading.set(true);
    this.documentService
      .bulkOperation({
        action: 'delete',
        document_ids: Array.from(this.selectedIds()),
      })
      .subscribe({
        next: (res) => {
          this.onBulkSuccess(`Deleted ${res.affected} document(s).`);
        },
        error: () => this.onBulkError('Failed to delete documents.'),
      });
  }

  private onBulkSuccess(message: string): void {
    this.bulkLoading.set(false);
    this.bulkMessage.set(message);
    this.bulkError.set(false);
    this.clearSelection();
    this.loadDocuments();
  }

  private onBulkError(message: string): void {
    this.bulkLoading.set(false);
    this.bulkMessage.set(message);
    this.bulkError.set(true);
  }
}
