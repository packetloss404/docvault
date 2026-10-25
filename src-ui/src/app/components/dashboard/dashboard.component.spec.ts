import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';

import { DashboardComponent, WidgetType } from './dashboard.component';
import { AuthService } from '../../services/auth.service';
import { DocumentService } from '../../services/document.service';
import { SearchService } from '../../services/search.service';
import { OrganizationService } from '../../services/organization.service';
import { PreferencesService } from '../../services/preferences.service';
import { EsignatureService } from '../../services/esignature.service';
import { ShellStatsService } from '../../services/shell-stats.service';
import { UploadService } from '../../services/upload.service';

// Mirror of DEFAULT_LAYOUT from dashboard.component.ts
const EXPECTED_DEFAULT_LAYOUT: WidgetType[] = [
  'welcome',
  'statistics',
  'recent_documents',
  'attention',
  'saved_views',
  'upload',
];

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;

  let mockDocumentService: {
    getDocuments: ReturnType<typeof vi.fn>;
    getDocumentTypes: ReturnType<typeof vi.fn>;
    getPreviewUrl: ReturnType<typeof vi.fn>;
  };
  let mockSearchService: {
    getDashboardViews: ReturnType<typeof vi.fn>;
  };
  let mockOrganizationService: {
    getTags: ReturnType<typeof vi.fn>;
    getCorrespondents: ReturnType<typeof vi.fn>;
  };
  let mockPreferencesService: {
    getPreferences: ReturnType<typeof vi.fn>;
    updatePreferences: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    mockDocumentService = {
      getDocuments: vi.fn().mockReturnValue(
        of({ count: 0, results: [], next: null, previous: null }),
      ),
      getDocumentTypes: vi.fn().mockReturnValue(
        of({ count: 0, results: [], next: null, previous: null }),
      ),
      getPreviewUrl: vi.fn().mockReturnValue('/api/v1/documents/1/preview/'),
    };

    mockSearchService = {
      getDashboardViews: vi.fn().mockReturnValue(of([])),
    };

    mockOrganizationService = {
      getTags: vi.fn().mockReturnValue(
        of({ count: 0, results: [], next: null, previous: null }),
      ),
      getCorrespondents: vi.fn().mockReturnValue(
        of({ count: 0, results: [], next: null, previous: null }),
      ),
    };

    mockPreferencesService = {
      getPreferences: vi.fn().mockReturnValue(of({})),
      updatePreferences: vi.fn().mockReturnValue(of({})),
    };

    // Ensure localStorage is clean so loadLayout uses server preferences path
    localStorage.removeItem('dv_dashboard_order');

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: DocumentService, useValue: mockDocumentService },
        { provide: SearchService, useValue: mockSearchService },
        { provide: OrganizationService, useValue: mockOrganizationService },
        { provide: PreferencesService, useValue: mockPreferencesService },
        {
          provide: AuthService,
          useValue: { currentUser: signal<{ username?: string } | null>(null) },
        },
        {
          provide: EsignatureService,
          useValue: { getRequests: vi.fn().mockReturnValue(of([])) },
        },
        {
          // ShellStatsService reaches for HttpClient, which this TestBed does
          // not provide; the dashboard only reads its signals.
          provide: ShellStatsService,
          useValue: {
            refresh: vi.fn(),
            activeTasks: () => 0,
            storageLabel: () => null,
            documentsLabel: () => null,
            ocrLabel: () => 'ocr idle',
            ocrBusy: () => false,
          },
        },
        {
          provide: UploadService,
          useValue: {
            pick: vi.fn(),
            upload: vi.fn(),
            uploading: () => false,
            message: () => '',
            error: () => false,
            completedTick: () => 0,
          },
        },
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    localStorage.removeItem('dv_dashboard_order');
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialise widgets with the default layout', () => {
    expect(component.widgets()).toEqual(EXPECTED_DEFAULT_LAYOUT);
  });

  describe('widget loading on init', () => {
    it('should call getDocuments to load statistics', () => {
      // loadStatistics calls getDocuments({ page_size: 1 }) for document count
      // and getDocuments({ page_size: 5, ordering: '-added' }) for recent docs
      expect(mockDocumentService.getDocuments).toHaveBeenCalled();
    });

    it('should call getDocumentTypes for statistics', () => {
      expect(mockDocumentService.getDocumentTypes).toHaveBeenCalled();
    });

    it('should call getTags for statistics', () => {
      expect(mockOrganizationService.getTags).toHaveBeenCalled();
    });

    it('should call getCorrespondents for statistics', () => {
      expect(mockOrganizationService.getCorrespondents).toHaveBeenCalled();
    });

    it('should call getDashboardViews', () => {
      expect(mockSearchService.getDashboardViews).toHaveBeenCalled();
    });
  });

  describe('initial signal state', () => {
    it('should start with statsLoading false after mocked responses resolve', () => {
      // All mocks emit synchronously via of(), so statsLoading should be false
      expect(component.statsLoading()).toBe(false);
    });

    it('should start with zero document count', () => {
      expect(component.documentCount()).toBe(0);
    });

    it('should start with empty recent documents', () => {
      expect(component.recentDocuments()).toEqual([]);
    });

    it('should start with empty dashboard views', () => {
      expect(component.dashboardViews()).toEqual([]);
    });

    it('should start with uploading false', () => {
      expect(component.uploading()).toBe(false);
    });

    it('should start with empty upload message', () => {
      expect(component.uploadMessage()).toBe('');
    });
  });

  describe('statistics loading with data', () => {
    beforeEach(async () => {
      mockDocumentService.getDocuments.mockImplementation((params: { page_size?: number; ordering?: string }) => {
        if (params.ordering === '-added') {
          return of({ count: 3, results: [
            { id: 1, title: 'Doc A', original_filename: 'a.pdf', added: '2024-01-01' },
          ], next: null, previous: null });
        }
        return of({ count: 42, results: [], next: null, previous: null });
      });
      mockDocumentService.getDocumentTypes.mockReturnValue(
        of({ count: 5, results: [], next: null, previous: null }),
      );
      mockOrganizationService.getTags.mockReturnValue(
        of({ count: 8, results: [], next: null, previous: null }),
      );
      mockOrganizationService.getCorrespondents.mockReturnValue(
        of({ count: 3, results: [], next: null, previous: null }),
      );

      // Re-create the component so ngOnInit picks up the updated mocks
      fixture = TestBed.createComponent(DashboardComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
    });

    it('should populate documentCount from getDocuments count', () => {
      expect(component.documentCount()).toBe(42);
    });

    it('should populate typeCount from getDocumentTypes count', () => {
      expect(component.typeCount()).toBe(5);
    });

    it('should populate tagCount from getTags count', () => {
      expect(component.tagCount()).toBe(8);
    });

    it('should populate correspondentCount from getCorrespondents count', () => {
      expect(component.correspondentCount()).toBe(3);
    });

    it('should populate recentDocuments', () => {
      expect(component.recentDocuments().length).toBe(1);
      expect(component.recentDocuments()[0].title).toBe('Doc A');
    });
  });

  describe('getWidgetTitle', () => {
    it('should return correct title for each widget type', () => {
      expect(component.getWidgetTitle('welcome')).toBe('Welcome');
      expect(component.getWidgetTitle('statistics')).toBe('Statistics');
      expect(component.getWidgetTitle('recent_documents')).toBe('Recent Documents');
      expect(component.getWidgetTitle('attention')).toBe('Needs your attention');
      expect(component.getWidgetTitle('saved_views')).toBe('Saved Views');
      expect(component.getWidgetTitle('upload')).toBe('Quick Upload');
    });
  });

  describe('layout regions', () => {
    it('spans the greeting and the stat row across the grid', () => {
      expect(component.isWideWidget('welcome')).toBe(true);
      expect(component.isWideWidget('statistics')).toBe(true);
    });

    it('keeps recent documents and the side cards in a column', () => {
      expect(component.isWideWidget('recent_documents')).toBe(false);
      expect(component.isWideWidget('attention')).toBe(false);
      expect(component.isWideWidget('saved_views')).toBe(false);
      expect(component.isWideWidget('upload')).toBe(false);
    });

    it('spans recent documents over the side cards beside it', () => {
      // attention + saved_views + upload
      expect(component.sideWidgetCount()).toBe(3);
    });

    it('never spans fewer than one row', () => {
      component.widgets.set(['welcome', 'statistics', 'recent_documents']);
      expect(component.sideWidgetCount()).toBe(1);
    });

    it('tracks the side-card count as the layout changes', () => {
      component.widgets.set(['recent_documents', 'upload']);
      expect(component.sideWidgetCount()).toBe(1);
    });
  });

  describe('greeting', () => {
    it('omits the name when no user is loaded', () => {
      expect(component.greeting()).toMatch(/^Good (morning|afternoon|evening)$/);
    });
  });

  describe('attention items', () => {
    it('is empty when nothing is pending', () => {
      component.pendingSignatures.set(0);
      expect(component.attentionItems()).toEqual([]);
    });

    it('reports pending signature requests', () => {
      component.pendingSignatures.set(2);
      const items = component.attentionItems();
      expect(items.length).toBe(1);
      expect(items[0].text).toBe('2 signature requests pending');
      expect(items[0].category).toBe('e-sign');
    });

    it('uses the singular for one request', () => {
      component.pendingSignatures.set(1);
      expect(component.attentionItems()[0].text).toBe('1 signature request pending');
    });
  });

  describe('resetLayout', () => {
    it('should restore default widget order', () => {
      component.widgets.set(['upload', 'welcome']);
      component.resetLayout();
      expect(component.widgets()).toEqual(EXPECTED_DEFAULT_LAYOUT);
    });

    it('should call updatePreferences to persist layout', () => {
      component.resetLayout();
      expect(mockPreferencesService.updatePreferences).toHaveBeenCalledWith({
        dashboard_layout: EXPECTED_DEFAULT_LAYOUT,
      });
    });
  });

  describe('onCdkDrop', () => {
    it('should reorder widgets when dropped at a different index', () => {
      component.widgets.set(['welcome', 'statistics', 'upload']);
      const event = { previousIndex: 0, currentIndex: 2 } as any;
      component.onCdkDrop(event);
      expect(component.widgets()).toEqual(['statistics', 'upload', 'welcome']);
    });

    it('should not reorder when dropped at the same index', () => {
      component.widgets.set(['welcome', 'statistics', 'upload']);
      const event = { previousIndex: 1, currentIndex: 1 } as any;
      component.onCdkDrop(event);
      expect(component.widgets()).toEqual(['welcome', 'statistics', 'upload']);
    });
  });

  describe('upload drag state', () => {
    it('should set uploadDragActive on dragover', () => {
      const event = { preventDefault: vi.fn(), stopPropagation: vi.fn() } as any;
      component.onUploadDragOver(event);
      expect(component.uploadDragActive()).toBe(true);
    });

    it('should clear uploadDragActive on drop', () => {
      component.uploadDragActive.set(true);
      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: { files: [] },
      } as any;
      component.onUploadDrop(event);
      expect(component.uploadDragActive()).toBe(false);
    });
  });

  describe('layout persistence via localStorage', () => {
    it('should load layout from localStorage when available', async () => {
      const savedLayout: WidgetType[] = ['upload', 'welcome', 'statistics', 'recent_documents', 'saved_views'];
      localStorage.setItem('dv_dashboard_order', JSON.stringify(savedLayout));

      fixture = TestBed.createComponent(DashboardComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();

      expect(component.widgets()).toEqual(savedLayout);
    });
  });
});
