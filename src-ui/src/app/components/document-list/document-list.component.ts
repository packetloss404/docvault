import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  DocumentService,
  DocumentQueryParams,
} from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';
import { UploadService } from '../../services/upload.service';
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
  /** Grid track for this column, used to build the row `--dv-cols`. */
  width: string;
  /** Right-align the cell (mono numerics and dates). */
  numeric?: boolean;
}

/** A removable filter token shown above the table. */
export interface FilterToken {
  key: 'search' | 'type';
  label: string;
}

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [DatePipe, FormsModule],
  templateUrl: './document-list.component.html',
  styleUrl: './document-list.component.scss',
})
export class DocumentListComponent implements OnInit {
  private readonly documentService = inject(DocumentService);
  private readonly organizationService = inject(OrganizationService);
  private readonly uploads = inject(UploadService);
  private readonly router = inject(Router);

  // --- Column configuration ---
  readonly availableColumns: ColumnDef[] = [
    { key: 'title', label: 'title', sortable: true, sortField: 'title', width: 'minmax(0, 1fr)' },
    { key: 'document_type', label: 'type', width: '110px' },
    { key: 'correspondent', label: 'correspondent', width: '150px' },
    { key: 'cabinet', label: 'cabinet', width: '150px' },
    { key: 'created', label: 'created', sortable: true, sortField: 'created', width: '96px', numeric: true },
    { key: 'added', label: 'added', sortable: true, sortField: 'added', width: '110px', numeric: true },
    { key: 'archive_serial_number', label: 'asn', width: '96px', numeric: true },
    { key: 'page_count', label: 'pages', width: '64px', numeric: true },
    { key: 'tags', label: 'tags', width: '150px' },
  ];

  readonly defaultColumns = ['title', 'document_type', 'correspondent', 'created'];

  selectedColumns = signal<string[]>(this.defaultColumns);
  showColumnDropdown = signal(false);
  showFilterPanel = signal(false);

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

  /** Draft search text, applied to `searchQuery` only on submit. */
  searchDraft = signal('');

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

  // Organization data for bulk actions and tag chips
  tags = signal<Tag[]>([]);
  correspondents = signal<Correspondent[]>([]);

  private readonly tagNames = computed(() => {
    const map = new Map<number, string>();
    for (const tag of this.tags()) map.set(tag.id, tag.name);
    return map;
  });

  // Bulk action form state
  selectedTagIds = signal<Set<number>>(new Set());
  selectedCorrespondentId = signal<number | null>(null);
  selectedDocTypeId = signal<number | null>(null);
  showDeleteConfirm = signal(false);

  readonly visibleColumns = computed(() =>
    this.availableColumns.filter((c) => this.selectedColumns().includes(c.key)),
  );

  /** `--dv-cols` for the header and every row: checkbox plus visible columns. */
  readonly gridColumns = computed(
    () => `28px ${this.visibleColumns().map((c) => c.width).join(' ')}`,
  );

  /** Active filters, rendered as removable tokens above the table. */
  readonly filterTokens = computed<FilterToken[]>(() => {
    const tokens: FilterToken[] = [];
    const search = this.searchQuery();
    if (search) tokens.push({ key: 'search', label: `search = "${search}"` });
    const typeId = this.selectedTypeId();
    if (typeId !== null) {
      const name =
        this.documentTypes().find((t) => t.id === typeId)?.name ?? String(typeId);
      tokens.push({ key: 'type', label: `type = ${name}` });
    }
    return tokens;
  });

  /** e.g. "created ↓" — the sort affordance on the right of the token row. */
  readonly sortLabel = computed(() => {
    const ordering = this.ordering();
    const descending = ordering.startsWith('-');
    const field = descending ? ordering.slice(1) : ordering;
    const label =
      this.availableColumns.find((c) => c.sortField === field)?.label ?? field;
    return `${label} ${descending ? '↓' : '↑'}`;
  });

  /** Condensed page list: 1 2 3 … 143, with gaps as null. */
  readonly pageItems = computed<(number | null)[]>(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    const pages = new Set<number>([1, total, current]);
    for (const offset of [-1, 1]) {
      const page = current + offset;
      if (page > 1 && page < total) pages.add(page);
    }
    // Keep a stable leading run so the control does not jump on page 1-3.
    if (current <= 3) [2, 3].forEach((p) => pages.add(p));
    if (current >= total - 2) [total - 1, total - 2].forEach((p) => pages.add(p));

    const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
    const items: (number | null)[] = [];
    let previous = 0;
    for (const page of sorted) {
      if (previous && page - previous > 1) items.push(null);
      items.push(page);
      previous = page;
    }
    return items;
  });

  ngOnInit(): void {
    this.loadColumnPrefs();
    this.loadDocumentTypes();
    this.loadTags();
    this.loadDocuments();
  }

  // --- Columns ---

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

  // --- Data ---

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

  // --- Filtering ---

  onSearch(): void {
    this.searchQuery.set(this.searchDraft().trim());
    this.currentPage.set(1);
    this.clearSelection();
    this.showFilterPanel.set(false);
    this.loadDocuments();
  }

  onTypeFilter(typeId: string): void {
    this.selectedTypeId.set(typeId ? Number(typeId) : null);
    this.currentPage.set(1);
    this.clearSelection();
    this.loadDocuments();
  }

  removeFilter(token: FilterToken): void {
    if (token.key === 'search') {
      this.searchQuery.set('');
      this.searchDraft.set('');
    } else {
      this.selectedTypeId.set(null);
    }
    this.currentPage.set(1);
    this.clearSelection();
    this.loadDocuments();
  }

  /** Cycles the sort direction of the column currently being sorted on. */
  toggleSortDirection(): void {
    const ordering = this.ordering();
    this.ordering.set(
      ordering.startsWith('-') ? ordering.slice(1) : `-${ordering}`,
    );
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

  /** Sort indicator glyph; blank when the column is not the sort key. */
  getSortGlyph(field: string): string {
    const current = this.ordering();
    if (current === field) return '↑';
    if (current === `-${field}`) return '↓';
    return '';
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadDocuments();
  }

  openDocument(doc: Document): void {
    this.router.navigate(['/documents', doc.id]);
  }

  upload(): void {
    this.uploads.pick();
  }

  /** Tag display names for a document's `tag_ids`, resolved where known. */
  tagLabels(doc: Document): string[] {
    const names = this.tagNames();
    return (doc.tag_ids ?? []).map((id) => names.get(id) ?? `#${id}`);
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
