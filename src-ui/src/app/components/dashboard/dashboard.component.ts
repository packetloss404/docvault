import { Component, OnInit, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import {
  CdkDragDrop,
  CdkDrag,
  CdkDragHandle,
  CdkDragPlaceholder,
  CdkDropList,
  moveItemInArray,
} from '@angular/cdk/drag-drop';
import { AuthService } from '../../services/auth.service';
import { DocumentService } from '../../services/document.service';
import { AuthenticatedSrcDirective } from '../../directives/authenticated-file.directive';
import { SearchService } from '../../services/search.service';
import { OrganizationService } from '../../services/organization.service';
import { EsignatureService } from '../../services/esignature.service';
import { ShellStatsService } from '../../services/shell-stats.service';
import { UploadService } from '../../services/upload.service';
import {
  PreferencesService,
  UserPreferences,
} from '../../services/preferences.service';
import { Document } from '../../models/document.model';
import { SavedViewListItem } from '../../models/search.model';

const DASHBOARD_ORDER_KEY = 'dv_dashboard_order';

export type WidgetType =
  | 'welcome'
  | 'statistics'
  | 'recent_documents'
  | 'attention'
  | 'saved_views'
  | 'upload';

const DEFAULT_LAYOUT: WidgetType[] = [
  'welcome',
  'statistics',
  'recent_documents',
  'attention',
  'saved_views',
  'upload',
];

/** One row of the "Needs your attention" card. */
export interface AttentionItem {
  text: string;
  category: string;
  tone: 'ok' | 'warn' | 'danger' | 'accent';
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    DatePipe,
    RouterModule,
    CdkDropList,
    CdkDrag,
    CdkDragHandle,
    CdkDragPlaceholder,
    AuthenticatedSrcDirective,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private readonly documentService = inject(DocumentService);
  private readonly searchService = inject(SearchService);
  private readonly organizationService = inject(OrganizationService);
  private readonly preferencesService = inject(PreferencesService);
  private readonly esignatures = inject(EsignatureService);
  private readonly auth = inject(AuthService);
  readonly shellStats = inject(ShellStatsService);
  readonly uploads = inject(UploadService);

  // Widget layout
  widgets = signal<WidgetType[]>([...DEFAULT_LAYOUT]);

  // Drag state
  dragSourceIndex = signal<number | null>(null);
  dragOverIndex = signal<number | null>(null);

  // Statistics widget
  statsLoading = signal(true);
  documentCount = signal(0);
  typeCount = signal(0);
  tagCount = signal(0);
  correspondentCount = signal(0);
  /** Documents added since the first of the current month. */
  addedThisMonth = signal<number | null>(null);

  // Recent documents widget
  recentLoading = signal(true);
  recentDocuments = signal<Document[]>([]);

  // Saved views widget
  dashboardViews = signal<SavedViewListItem[]>([]);

  // Attention widget
  pendingSignatures = signal<number | null>(null);

  // Upload widget — mirrors UploadService so existing tests and template keep working
  uploading = signal(false);
  uploadDragActive = signal(false);
  uploadMessage = signal('');
  uploadError = signal(false);

  readonly now = new Date();

  readonly greeting = computed(() => {
    const hour = this.now.getHours();
    const timeOfDay =
      hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const name = this.auth.currentUser()?.username;
    return name ? `${timeOfDay}, ${name}` : timeOfDay;
  });

  /** Secondary mono line: counts the design does not give a stat card. */
  readonly libraryLine = computed(
    () =>
      `${this.typeCount()} types · ${this.tagCount()} tags · ${this.correspondentCount()} correspondents`,
  );

  readonly attentionItems = computed<AttentionItem[]>(() => {
    const items: AttentionItem[] = [];
    const pending = this.pendingSignatures();
    if (pending) {
      items.push({
        text: `${pending} signature request${pending === 1 ? '' : 's'} pending`,
        category: 'e-sign',
        tone: 'accent',
      });
    }
    const active = this.shellStats.activeTasks();
    if (active) {
      items.push({
        text: `${active} document${active === 1 ? '' : 's'} still processing`,
        category: 'ingest',
        tone: 'warn',
      });
    }
    return items;
  });

  constructor() {
    // Keep the local upload mirrors in step with the shared service, so the
    // shell's Upload button and this widget report the same state.
    effect(() => {
      this.uploading.set(this.uploads.uploading());
      this.uploadMessage.set(this.uploads.message());
      this.uploadError.set(this.uploads.error());
    });
    // Refresh lists after any upload completes, wherever it was started.
    effect(() => {
      if (this.uploads.completedTick() > 0) {
        this.loadStatistics();
        this.loadRecentDocuments();
      }
    });
  }

  ngOnInit(): void {
    this.loadLayout();
    this.loadStatistics();
    this.loadRecentDocuments();
    this.loadDashboardViews();
    this.loadAttention();
  }

  // --- Layout persistence ---

  loadLayout(): void {
    // Try localStorage first (fast, offline-capable)
    try {
      const stored = localStorage.getItem(DASHBOARD_ORDER_KEY);
      if (stored) {
        const parsed: WidgetType[] = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this.widgets.set(parsed);
          return;
        }
      }
    } catch {
      // Fall through to preferences service
    }

    this.preferencesService.getPreferences().subscribe({
      next: (prefs: UserPreferences) => {
        if (
          prefs.dashboard_layout &&
          Array.isArray(prefs.dashboard_layout) &&
          prefs.dashboard_layout.length > 0
        ) {
          this.widgets.set(prefs.dashboard_layout as WidgetType[]);
        }
      },
      error: () => {
        // Use default layout on error
      },
    });
  }

  saveLayout(): void {
    const layout = this.widgets();
    try {
      localStorage.setItem(DASHBOARD_ORDER_KEY, JSON.stringify(layout));
    } catch {
      // Ignore storage errors
    }
    this.preferencesService
      .updatePreferences({ dashboard_layout: layout })
      .subscribe();
  }

  resetLayout(): void {
    this.widgets.set([...DEFAULT_LAYOUT]);
    this.saveLayout();
  }

  /** The greeting and the stat row span the full grid width. */
  isWideWidget(widget: WidgetType): boolean {
    return widget === 'welcome' || widget === 'statistics';
  }

  /**
   * How many rows the recent-documents card should span so the side cards stack
   * beside it in the narrow column, as the design's 1.6fr/1fr split shows.
   */
  readonly sideWidgetCount = computed(() =>
    Math.max(
      1,
      this.widgets().filter(
        (w) => !this.isWideWidget(w) && w !== 'recent_documents',
      ).length,
    ),
  );

  // --- CDK Drag & drop reordering ---

  onCdkDrop(event: CdkDragDrop<WidgetType[]>): void {
    if (event.previousIndex !== event.currentIndex) {
      const layout = [...this.widgets()];
      moveItemInArray(layout, event.previousIndex, event.currentIndex);
      this.widgets.set(layout);
      this.saveLayout();
    }
  }

  // --- Widget data loading ---

  loadStatistics(): void {
    this.statsLoading.set(true);
    let remaining = 4;
    const checkDone = () => {
      remaining--;
      if (remaining === 0) this.statsLoading.set(false);
    };

    this.documentService.getDocuments({ page_size: 1 }).subscribe({
      next: (res) => {
        this.documentCount.set(res.count);
        checkDone();
      },
      error: () => checkDone(),
    });

    this.documentService.getDocumentTypes().subscribe({
      next: (res) => {
        this.typeCount.set(res.count);
        checkDone();
      },
      error: () => checkDone(),
    });

    this.organizationService.getTags().subscribe({
      next: (res) => {
        this.tagCount.set(res.count);
        checkDone();
      },
      error: () => checkDone(),
    });

    this.organizationService.getCorrespondents().subscribe({
      next: (res) => {
        this.correspondentCount.set(res.count);
        checkDone();
      },
      error: () => checkDone(),
    });

    // Month-to-date delta for the documents stat card.
    const monthStart = new Date(this.now.getFullYear(), this.now.getMonth(), 1);
    this.documentService
      .getDocuments({
        page_size: 1,
        created_after: monthStart.toISOString().slice(0, 10),
      })
      .subscribe({
        next: (res) => this.addedThisMonth.set(res.count),
        error: () => this.addedThisMonth.set(null),
      });
  }

  loadRecentDocuments(): void {
    this.recentLoading.set(true);
    this.documentService
      .getDocuments({ page_size: 5, ordering: '-added' })
      .subscribe({
        next: (res) => {
          this.recentDocuments.set(res.results);
          this.recentLoading.set(false);
        },
        error: () => this.recentLoading.set(false),
      });
  }

  loadDashboardViews(): void {
    this.searchService.getDashboardViews().subscribe({
      next: (views) => this.dashboardViews.set(views),
    });
  }

  loadAttention(): void {
    this.esignatures.getRequests({ status: 'pending' }).subscribe({
      next: (requests) => this.pendingSignatures.set(requests?.length ?? 0),
      error: () => this.pendingSignatures.set(null),
    });
  }

  getWidgetTitle(type: WidgetType): string {
    const titles: Record<WidgetType, string> = {
      welcome: 'Welcome',
      statistics: 'Statistics',
      recent_documents: 'Recent Documents',
      attention: 'Needs your attention',
      saved_views: 'Saved Views',
      upload: 'Quick Upload',
    };
    return titles[type];
  }

  getPreviewUrl(doc: Document): string {
    return this.documentService.getPreviewUrl(doc.id);
  }


  // --- Upload handling ---

  pickFiles(): void {
    this.uploads.pick();
  }

  onUploadDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadDragActive.set(true);
  }

  onUploadDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadDragActive.set(false);
  }

  onUploadDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadDragActive.set(false);
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploads.upload(files);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploads.upload(input.files);
      input.value = '';
    }
  }
}
