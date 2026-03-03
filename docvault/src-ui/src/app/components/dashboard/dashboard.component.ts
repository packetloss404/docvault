import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DocumentService } from '../../services/document.service';
import { SearchService } from '../../services/search.service';
import { OrganizationService } from '../../services/organization.service';
import {
  PreferencesService,
  UserPreferences,
} from '../../services/preferences.service';
import { Document } from '../../models/document.model';
import { SavedViewListItem } from '../../models/search.model';

export type WidgetType =
  | 'welcome'
  | 'statistics'
  | 'recent_documents'
  | 'saved_views'
  | 'upload';

const DEFAULT_LAYOUT: WidgetType[] = [
  'welcome',
  'statistics',
  'recent_documents',
  'saved_views',
  'upload',
];

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="mb-0">Dashboard</h2>
      <button
        class="btn btn-sm btn-outline-secondary"
        (click)="resetLayout()"
        title="Reset widget layout to defaults"
      >
        <i class="bi bi-arrow-counterclockwise me-1"></i>Reset Layout
      </button>
    </div>

    <div class="row g-4">
      @for (widget of widgets(); track widget; let i = $index) {
        <div
          class="col-md-6"
          [attr.draggable]="true"
          (dragstart)="onDragStart($event, i)"
          (dragover)="onDragOver($event, i)"
          (dragenter)="onDragEnter($event, i)"
          (dragleave)="onDragLeave($event)"
          (drop)="onDrop($event, i)"
          (dragend)="onDragEnd($event)"
          [class.dv-drag-over]="dragOverIndex() === i && dragSourceIndex() !== i"
        >
          <!-- Widget Card -->
          <div class="card h-100 dv-widget-card">
            <div class="card-header d-flex align-items-center">
              <i
                class="bi bi-grip-vertical me-2 text-muted dv-drag-handle"
                style="cursor: grab;"
              ></i>
              <span class="fw-semibold">{{ getWidgetTitle(widget) }}</span>
            </div>

            <!-- Statistics Widget -->
            @if (widget === 'statistics') {
              <div class="card-body">
                @if (statsLoading()) {
                  <div class="text-center py-3">
                    <div
                      class="spinner-border spinner-border-sm text-primary"
                      role="status"
                    ></div>
                  </div>
                } @else {
                  <div class="row g-3">
                    <div class="col-6">
                      <div class="d-flex align-items-center">
                        <div
                          class="bg-primary bg-opacity-10 rounded-3 p-2 me-2"
                        >
                          <i
                            class="bi bi-file-earmark-text text-primary"
                          ></i>
                        </div>
                        <div>
                          <div class="text-muted small">Documents</div>
                          <div class="fw-bold fs-5">
                            {{ documentCount() }}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="col-6">
                      <div class="d-flex align-items-center">
                        <div
                          class="bg-success bg-opacity-10 rounded-3 p-2 me-2"
                        >
                          <i class="bi bi-collection text-success"></i>
                        </div>
                        <div>
                          <div class="text-muted small">Types</div>
                          <div class="fw-bold fs-5">
                            {{ typeCount() }}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="col-6">
                      <div class="d-flex align-items-center">
                        <div
                          class="bg-warning bg-opacity-10 rounded-3 p-2 me-2"
                        >
                          <i class="bi bi-tags text-warning"></i>
                        </div>
                        <div>
                          <div class="text-muted small">Tags</div>
                          <div class="fw-bold fs-5">{{ tagCount() }}</div>
                        </div>
                      </div>
                    </div>
                    <div class="col-6">
                      <div class="d-flex align-items-center">
                        <div
                          class="bg-info bg-opacity-10 rounded-3 p-2 me-2"
                        >
                          <i class="bi bi-people text-info"></i>
                        </div>
                        <div>
                          <div class="text-muted small">Correspondents</div>
                          <div class="fw-bold fs-5">
                            {{ correspondentCount() }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                }
              </div>
            }

            <!-- Recent Documents Widget -->
            @if (widget === 'recent_documents') {
              <div class="card-body p-0">
                @if (recentLoading()) {
                  <div class="text-center py-3">
                    <div
                      class="spinner-border spinner-border-sm text-primary"
                      role="status"
                    ></div>
                  </div>
                } @else if (recentDocuments().length === 0) {
                  <div class="text-center text-muted py-4">
                    <i class="bi bi-folder2-open fs-3"></i>
                    <p class="mt-2 mb-0">No documents yet.</p>
                  </div>
                } @else {
                  <div class="list-group list-group-flush">
                    @for (
                      doc of recentDocuments();
                      track doc.id
                    ) {
                      <a
                        [routerLink]="['/documents', doc.id]"
                        class="list-group-item list-group-item-action"
                      >
                        <div class="d-flex justify-content-between">
                          <div>
                            <div class="fw-semibold">{{ doc.title }}</div>
                            <small class="text-muted">{{
                              doc.original_filename
                            }}</small>
                          </div>
                          <small class="text-muted">{{
                            doc.added | date: 'shortDate'
                          }}</small>
                        </div>
                      </a>
                    }
                  </div>
                  <div class="card-footer text-center">
                    <a
                      routerLink="/documents"
                      class="btn btn-sm btn-outline-primary"
                      >View All Documents</a
                    >
                  </div>
                }
              </div>
            }

            <!-- Upload Widget -->
            @if (widget === 'upload') {
              <div class="card-body">
                <div
                  class="border border-2 border-dashed rounded-3 p-4 text-center"
                  [class.border-primary]="uploadDragActive()"
                  [class.bg-primary]="uploadDragActive()"
                  [class.bg-opacity-10]="uploadDragActive()"
                  (dragover)="onUploadDragOver($event)"
                  (dragleave)="uploadDragActive.set(false)"
                  (drop)="onUploadDrop($event)"
                >
                  @if (uploading()) {
                    <div
                      class="spinner-border text-primary mb-2"
                      role="status"
                    ></div>
                    <p class="mb-0">Uploading...</p>
                  } @else {
                    <i class="bi bi-cloud-arrow-up fs-1 text-muted"></i>
                    <p class="mb-2 text-muted">
                      Drag & drop files here, or click to browse
                    </p>
                    <label class="btn btn-outline-primary btn-sm">
                      <i class="bi bi-plus-lg me-1"></i>Choose Files
                      <input
                        type="file"
                        class="d-none"
                        multiple
                        (change)="onFileSelected($event)"
                      />
                    </label>
                  }
                </div>
                @if (uploadMessage()) {
                  <div
                    class="alert mt-3 mb-0"
                    [class.alert-success]="!uploadError()"
                    [class.alert-danger]="uploadError()"
                  >
                    {{ uploadMessage() }}
                  </div>
                }
              </div>
            }

            <!-- Saved Views Widget -->
            @if (widget === 'saved_views') {
              <div class="card-body p-0">
                @if (dashboardViews().length === 0) {
                  <div class="text-center text-muted py-4">
                    <i class="bi bi-bookmarks fs-3"></i>
                    <p class="mt-2 mb-0">
                      No saved views on the dashboard.
                    </p>
                  </div>
                } @else {
                  <div class="list-group list-group-flush">
                    @for (
                      view of dashboardViews();
                      track view.id
                    ) {
                      <div
                        class="list-group-item d-flex justify-content-between align-items-center"
                      >
                        <div>
                          <i class="bi bi-bookmark me-1"></i>
                          <span class="fw-semibold">{{ view.name }}</span>
                          <small class="text-muted ms-2">
                            {{ view.display_mode }} &middot;
                            {{ view.rule_count }} filter rule{{
                              view.rule_count !== 1 ? 's' : ''
                            }}
                          </small>
                        </div>
                        <a
                          [routerLink]="[
                            '/saved-views',
                            view.id,
                            'results'
                          ]"
                          class="btn btn-sm btn-outline-primary"
                          >View</a
                        >
                      </div>
                    }
                  </div>
                }
              </div>
            }

            <!-- Welcome Widget -->
            @if (widget === 'welcome') {
              <div class="card-body">
                <h5 class="card-title">
                  <i class="bi bi-hand-wave me-2"></i>Welcome to DocVault
                </h5>
                <p class="card-text text-muted">
                  Your document management system is ready. Here are
                  some tips to get started:
                </p>
                <ul class="list-unstyled mb-0">
                  <li class="mb-2">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <a routerLink="/documents" class="text-decoration-none"
                      >Upload your first document</a
                    >
                  </li>
                  <li class="mb-2">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <a routerLink="/tags" class="text-decoration-none"
                      >Create tags to organize documents</a
                    >
                  </li>
                  <li class="mb-2">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <a
                      routerLink="/correspondents"
                      class="text-decoration-none"
                      >Set up correspondents</a
                    >
                  </li>
                  <li class="mb-2">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <a routerLink="/saved-views" class="text-decoration-none"
                      >Create saved views for quick access</a
                    >
                  </li>
                  <li>
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <span>Drag widgets to customize your dashboard layout</span>
                  </li>
                </ul>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .dv-widget-card {
        transition: box-shadow 0.2s ease;
      }
      .dv-widget-card:hover {
        box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.1);
      }
      .dv-drag-handle {
        font-size: 1.2rem;
      }
      .dv-drag-over {
        outline: 2px dashed var(--bs-primary);
        outline-offset: -2px;
        border-radius: 0.375rem;
      }
      .border-dashed {
        border-style: dashed !important;
      }
      .list-group-item {
        background-color: var(--dv-card-bg, #ffffff);
        color: var(--dv-text, #212529);
        border-color: var(--dv-border, #dee2e6);
      }
    `,
  ],
})
export class DashboardComponent implements OnInit {
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

  // Recent documents widget
  recentLoading = signal(true);
  recentDocuments = signal<Document[]>([]);

  // Saved views widget
  dashboardViews = signal<SavedViewListItem[]>([]);

  // Upload widget
  uploading = signal(false);
  uploadDragActive = signal(false);
  uploadMessage = signal('');
  uploadError = signal(false);

  constructor(
    private documentService: DocumentService,
    private searchService: SearchService,
    private organizationService: OrganizationService,
    private preferencesService: PreferencesService,
  ) {}

  ngOnInit(): void {
    this.loadLayout();
    this.loadStatistics();
    this.loadRecentDocuments();
    this.loadDashboardViews();
  }

  // --- Layout persistence ---

  loadLayout(): void {
    this.preferencesService.getPreferences().subscribe({
      next: (prefs: UserPreferences) => {
        if (prefs.dashboard_layout && Array.isArray(prefs.dashboard_layout) && prefs.dashboard_layout.length > 0) {
          this.widgets.set(prefs.dashboard_layout as WidgetType[]);
        }
      },
      error: () => {
        // Use default layout on error
      },
    });
  }

  saveLayout(): void {
    this.preferencesService
      .updatePreferences({ dashboard_layout: this.widgets() })
      .subscribe();
  }

  resetLayout(): void {
    this.widgets.set([...DEFAULT_LAYOUT]);
    this.saveLayout();
  }

  // --- Drag & drop reordering ---

  onDragStart(event: DragEvent, index: number): void {
    this.dragSourceIndex.set(index);
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', String(index));
    }
  }

  onDragOver(event: DragEvent, index: number): void {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
  }

  onDragEnter(event: DragEvent, index: number): void {
    event.preventDefault();
    this.dragOverIndex.set(index);
  }

  onDragLeave(event: DragEvent): void {
    // Only clear if leaving the container area
    const relatedTarget = event.relatedTarget as HTMLElement;
    if (!relatedTarget || !(event.currentTarget as HTMLElement).contains(relatedTarget)) {
      this.dragOverIndex.set(null);
    }
  }

  onDrop(event: DragEvent, targetIndex: number): void {
    event.preventDefault();
    const sourceIndex = this.dragSourceIndex();
    if (sourceIndex !== null && sourceIndex !== targetIndex) {
      const layout = [...this.widgets()];
      const [moved] = layout.splice(sourceIndex, 1);
      layout.splice(targetIndex, 0, moved);
      this.widgets.set(layout);
      this.saveLayout();
    }
    this.dragSourceIndex.set(null);
    this.dragOverIndex.set(null);
  }

  onDragEnd(event: DragEvent): void {
    this.dragSourceIndex.set(null);
    this.dragOverIndex.set(null);
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

  // --- Upload handling ---

  onUploadDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadDragActive.set(true);
  }

  onUploadDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadDragActive.set(false);
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploadFiles(files);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFiles(input.files);
      input.value = '';
    }
  }

  private uploadFiles(files: FileList): void {
    this.uploading.set(true);
    this.uploadMessage.set('');
    this.uploadError.set(false);

    let completed = 0;
    let errors = 0;
    const total = files.length;

    for (let i = 0; i < files.length; i++) {
      const formData = new FormData();
      formData.append('document', files[i]);
      formData.append('title', files[i].name);

      this.documentService.createDocument(formData as unknown as Partial<Document>).subscribe({
        next: () => {
          completed++;
          if (completed + errors === total) {
            this.onUploadComplete(completed, errors);
          }
        },
        error: () => {
          errors++;
          if (completed + errors === total) {
            this.onUploadComplete(completed, errors);
          }
        },
      });
    }
  }

  private onUploadComplete(completed: number, errors: number): void {
    this.uploading.set(false);
    if (errors === 0) {
      this.uploadMessage.set(
        `Successfully uploaded ${completed} file${completed !== 1 ? 's' : ''}.`,
      );
      this.uploadError.set(false);
      this.loadStatistics();
      this.loadRecentDocuments();
    } else {
      this.uploadMessage.set(
        `Uploaded ${completed} file${completed !== 1 ? 's' : ''}, ${errors} failed.`,
      );
      this.uploadError.set(true);
    }
    setTimeout(() => this.uploadMessage.set(''), 5000);
  }

  // --- Helpers ---

  getWidgetTitle(type: WidgetType): string {
    const titles: Record<WidgetType, string> = {
      welcome: 'Welcome',
      statistics: 'Statistics',
      recent_documents: 'Recent Documents',
      saved_views: 'Saved Views',
      upload: 'Quick Upload',
    };
    return titles[type] || type;
  }
}
