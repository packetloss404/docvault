import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { DocumentListComponent } from './document-list.component';
import { DocumentService } from '../../services/document.service';
import { OrganizationService } from '../../services/organization.service';

const makeDocPage = (docs: Partial<{ id: number; title: string }>[] = []) => ({
  count: docs.length,
  results: docs as any[],
  next: null,
  previous: null,
});

const makeTypePage = (types: Partial<{ id: number; name: string }>[] = []) => ({
  count: types.length,
  results: types as any[],
  next: null,
  previous: null,
});

describe('DocumentListComponent', () => {
  let component: DocumentListComponent;
  let fixture: ComponentFixture<DocumentListComponent>;

  let mockDocumentService: {
    getDocuments: ReturnType<typeof vi.fn>;
    getDocumentTypes: ReturnType<typeof vi.fn>;
    bulkOperation: ReturnType<typeof vi.fn>;
    getPreviewUrl: ReturnType<typeof vi.fn>;
  };
  let mockOrganizationService: {
    getTags: ReturnType<typeof vi.fn>;
    getCorrespondents: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    mockDocumentService = {
      getDocuments: vi.fn().mockReturnValue(of(makeDocPage())),
      getDocumentTypes: vi.fn().mockReturnValue(of(makeTypePage())),
      bulkOperation: vi.fn().mockReturnValue(of({ affected: 0 })),
      getPreviewUrl: vi.fn().mockReturnValue('/api/documents/1/preview/'),
    };

    mockOrganizationService = {
      getTags: vi.fn().mockReturnValue(of({ count: 0, results: [], next: null, previous: null })),
      getCorrespondents: vi.fn().mockReturnValue(of({ count: 0, results: [], next: null, previous: null })),
    };

    // Clear column prefs so each test starts fresh
    localStorage.removeItem('dv_doc_list_columns');

    await TestBed.configureTestingModule({
      imports: [DocumentListComponent],
      providers: [
        { provide: DocumentService, useValue: mockDocumentService },
        { provide: OrganizationService, useValue: mockOrganizationService },
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    localStorage.removeItem('dv_doc_list_columns');
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // --- Column configuration ---

  describe('column configuration', () => {
    it('should expose 9 available columns', () => {
      expect(component.availableColumns.length).toBe(9);
    });

    it('should include expected column keys', () => {
      const keys = component.availableColumns.map((c) => c.key);
      expect(keys).toContain('title');
      expect(keys).toContain('document_type');
      expect(keys).toContain('correspondent');
      expect(keys).toContain('created');
      expect(keys).toContain('added');
      expect(keys).toContain('tags');
    });

    it('should start with the four default columns selected', () => {
      expect(component.selectedColumns()).toEqual([
        'title',
        'document_type',
        'correspondent',
        'created',
      ]);
    });

    it('isColumnSelected returns true for a selected column', () => {
      expect(component.isColumnSelected('title')).toBe(true);
    });

    it('isColumnSelected returns false for a non-selected column', () => {
      expect(component.isColumnSelected('tags')).toBe(false);
    });

    it('toggleColumn adds a column and keeps declaration order', () => {
      component.toggleColumn('added');
      const selected = component.selectedColumns();
      expect(selected).toContain('added');
      // 'added' should appear after 'created' (index 5 vs 4 in availableColumns)
      const createdIdx = selected.indexOf('created');
      const addedIdx = selected.indexOf('added');
      expect(addedIdx).toBeGreaterThan(createdIdx);
    });

    it('toggleColumn removes an existing column', () => {
      component.toggleColumn('correspondent');
      expect(component.selectedColumns()).not.toContain('correspondent');
    });

    it('toggleColumn does not remove the last remaining column', () => {
      // Remove all but one
      component.selectedColumns.set(['title']);
      component.toggleColumn('title');
      expect(component.selectedColumns()).toEqual(['title']);
    });

    it('showColumnDropdown starts as false', () => {
      expect(component.showColumnDropdown()).toBe(false);
    });
  });

  // --- Loading state ---

  describe('loading state', () => {
    it('should set loading to false after documents load (synchronous mock)', () => {
      expect(component.loading()).toBe(false);
    });

    it('should start with empty documents array', () => {
      expect(component.documents()).toEqual([]);
    });

    it('should start with totalCount 0', () => {
      expect(component.totalCount()).toBe(0);
    });

    it('should call getDocuments on init', () => {
      expect(mockDocumentService.getDocuments).toHaveBeenCalled();
    });

    it('should call getDocumentTypes on init', () => {
      expect(mockDocumentService.getDocumentTypes).toHaveBeenCalled();
    });
  });

  // --- Documents rendering ---

  describe('with documents loaded', () => {
    const sampleDocs = [
      { id: 1, title: 'Invoice Q1', created: '2024-01-10', original_filename: 'inv.pdf', tags: [] },
      { id: 2, title: 'Contract 2024', created: '2024-02-15', original_filename: 'contract.pdf', tags: [] },
    ];

    beforeEach(() => {
      mockDocumentService.getDocuments.mockReturnValue(
        of({ count: 2, results: sampleDocs, next: null, previous: null }),
      );
      component.loadDocuments();
    });

    it('should populate documents signal', () => {
      expect(component.documents().length).toBe(2);
      expect(component.documents()[0].title).toBe('Invoice Q1');
    });

    it('should set totalCount', () => {
      expect(component.totalCount()).toBe(2);
    });

    it('should set loading to false after load', () => {
      expect(component.loading()).toBe(false);
    });
  });

  // --- Pagination ---

  describe('pagination', () => {
    it('should start on page 1', () => {
      expect(component.currentPage()).toBe(1);
    });

    it('should have default page size of 25', () => {
      expect(component.pageSize()).toBe(25);
    });

    it('totalPages computed correctly', () => {
      component.totalCount.set(75);
      expect(component.totalPages()).toBe(3);
    });

    it('goToPage ignores out-of-range pages', () => {
      component.totalCount.set(25); // 1 page
      component.goToPage(0);
      expect(component.currentPage()).toBe(1);
      component.goToPage(2);
      expect(component.currentPage()).toBe(1);
    });

    it('goToPage advances to a valid page', () => {
      component.totalCount.set(100); // 4 pages
      component.goToPage(3);
      expect(component.currentPage()).toBe(3);
      expect(mockDocumentService.getDocuments).toHaveBeenCalled();
    });
  });

  // --- Search & filter ---

  describe('search and filter', () => {
    it('onSearch resets to page 1', () => {
      component.currentPage.set(3);
      component.onSearch();
      expect(component.currentPage()).toBe(1);
    });

    it('onSearch calls getDocuments', () => {
      const callsBefore = mockDocumentService.getDocuments.mock.calls.length;
      component.onSearch();
      expect(mockDocumentService.getDocuments.mock.calls.length).toBeGreaterThan(callsBefore);
    });

    it('onTypeFilter sets selectedTypeId and resets page', () => {
      component.currentPage.set(2);
      component.onTypeFilter('5');
      expect(component.selectedTypeId()).toBe(5);
      expect(component.currentPage()).toBe(1);
    });

    it('onTypeFilter clears selectedTypeId when empty string passed', () => {
      component.selectedTypeId.set(5);
      component.onTypeFilter('');
      expect(component.selectedTypeId()).toBeNull();
    });
  });

  // --- Sorting ---

  describe('sortBy', () => {
    it('should set ordering to field on first call', () => {
      component.ordering.set('-created');
      component.sortBy('title');
      expect(component.ordering()).toBe('title');
    });

    it('should toggle to descending when already ascending', () => {
      component.ordering.set('title');
      component.sortBy('title');
      expect(component.ordering()).toBe('-title');
    });

    it('should toggle to ascending when already descending', () => {
      component.ordering.set('-title');
      component.sortBy('title');
      expect(component.ordering()).toBe('title');
    });

    it('getSortIcon returns correct icon class', () => {
      component.ordering.set('title');
      expect(component.getSortIcon('title')).toBe('bi-sort-up');

      component.ordering.set('-title');
      expect(component.getSortIcon('title')).toBe('bi-sort-down');

      component.ordering.set('created');
      expect(component.getSortIcon('title')).toBe('bi-chevron-expand');
    });
  });

  // --- Selection ---

  describe('selection', () => {
    beforeEach(() => {
      mockDocumentService.getDocuments.mockReturnValue(
        of({ count: 3, results: [
          { id: 1, title: 'A', tags: [] },
          { id: 2, title: 'B', tags: [] },
          { id: 3, title: 'C', tags: [] },
        ], next: null, previous: null }),
      );
      component.loadDocuments();
    });

    it('should start with no selection', () => {
      expect(component.hasSelection()).toBe(false);
      expect(component.selectionCount()).toBe(0);
    });

    it('toggleSelect adds a document to selection', () => {
      const stopProp = vi.fn();
      component.toggleSelect(1, { stopPropagation: stopProp } as any);
      expect(component.isSelected(1)).toBe(true);
      expect(component.selectionCount()).toBe(1);
    });

    it('toggleSelect removes an already-selected document', () => {
      const evt = { stopPropagation: vi.fn() } as any;
      component.toggleSelect(1, evt);
      component.toggleSelect(1, evt);
      expect(component.isSelected(1)).toBe(false);
    });

    it('toggleSelectAll selects all documents', () => {
      component.toggleSelectAll();
      expect(component.allSelected()).toBe(true);
      expect(component.selectionCount()).toBe(3);
    });

    it('toggleSelectAll deselects all when all are already selected', () => {
      component.toggleSelectAll();
      component.toggleSelectAll();
      expect(component.allSelected()).toBe(false);
      expect(component.selectionCount()).toBe(0);
    });

    it('clearSelection empties the selection', () => {
      component.toggleSelectAll();
      component.clearSelection();
      expect(component.selectionCount()).toBe(0);
      expect(component.hasSelection()).toBe(false);
    });
  });

  // --- Bulk actions ---

  describe('bulk actions', () => {
    it('openBulkAction sets bulkAction signal', () => {
      component.openBulkAction('delete');
      expect(component.bulkAction()).toBe('delete');
      expect(component.showDeleteConfirm()).toBe(true);
    });

    it('openBulkAction for add_tags calls getTags', () => {
      component.openBulkAction('add_tags');
      expect(mockOrganizationService.getTags).toHaveBeenCalled();
    });

    it('openBulkAction for set_correspondent calls getCorrespondents', () => {
      component.openBulkAction('set_correspondent');
      expect(mockOrganizationService.getCorrespondents).toHaveBeenCalled();
    });

    it('cancelBulkAction clears bulkAction', () => {
      component.openBulkAction('delete');
      component.cancelBulkAction();
      expect(component.bulkAction()).toBeNull();
      expect(component.showDeleteConfirm()).toBe(false);
    });
  });

  // --- Column prefs persistence ---

  describe('column preference persistence', () => {
    it('saveColumnPrefs writes to localStorage', () => {
      component.selectedColumns.set(['title', 'added']);
      component.saveColumnPrefs();
      const stored = localStorage.getItem('dv_doc_list_columns');
      expect(stored).toBe(JSON.stringify(['title', 'added']));
    });

    it('loadColumnPrefs reads valid columns from localStorage', () => {
      localStorage.setItem('dv_doc_list_columns', JSON.stringify(['title', 'tags']));
      component.loadColumnPrefs();
      expect(component.selectedColumns()).toEqual(['title', 'tags']);
    });

    it('loadColumnPrefs ignores unknown column keys', () => {
      localStorage.setItem('dv_doc_list_columns', JSON.stringify(['title', 'nonexistent']));
      component.loadColumnPrefs();
      expect(component.selectedColumns()).toEqual(['title']);
    });

    it('loadColumnPrefs falls back to defaults if stored array is empty', () => {
      localStorage.setItem('dv_doc_list_columns', JSON.stringify([]));
      // valid.length === 0 means it won't set — stays at whatever selectedColumns is
      const before = component.selectedColumns();
      component.loadColumnPrefs();
      expect(component.selectedColumns()).toEqual(before);
    });
  });
});
