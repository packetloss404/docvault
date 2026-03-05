import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { EntityService } from '../../services/entity.service';
import { EntityAggregate, EntityType } from '../../models/entity.model';

@Component({
  selector: 'app-entity-browser',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <h2 class="mb-4">Entity Browser</h2>

    <div class="row">
      <!-- Left Sidebar: Entity Type Filters -->
      <div class="col-md-3">
        <div class="card">
          <div class="card-header">
            <h6 class="mb-0">Entity Types</h6>
          </div>
          <div class="card-body">
            @for (et of entityTypes(); track et.id) {
              <div class="form-check mb-2">
                <input
                  class="form-check-input"
                  type="checkbox"
                  [id]="'et-' + et.id"
                  [checked]="selectedTypes().has(et.name)"
                  (change)="toggleType(et.name)"
                />
                <label class="form-check-label d-flex align-items-center gap-2" [for]="'et-' + et.id">
                  <span
                    class="badge"
                    [style.background]="et.color"
                    [style.color]="getContrastColor(et.color)"
                  >
                    <i class="bi" [ngClass]="et.icon || 'bi-tag'"></i>
                    {{ et.label || et.name }}
                  </span>
                </label>
              </div>
            } @empty {
              <p class="text-muted small">No entity types configured.</p>
            }
          </div>
        </div>

        <!-- Search -->
        <div class="card mt-3">
          <div class="card-body">
            <label class="form-label">Search Entities</label>
            <div class="input-group">
              <input
                type="text"
                class="form-control"
                [(ngModel)]="searchQuery"
                (keyup.enter)="loadEntities()"
                placeholder="Filter by value..."
              />
              <button class="btn btn-outline-secondary" (click)="loadEntities()">
                <i class="bi bi-search"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="col-md-9">
        @if (loading()) {
          <div class="text-center py-5">
            <div class="spinner-border" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
        } @else {
          <!-- Entity List -->
          @if (!selectedEntity()) {
            <div class="card">
              <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Entities ({{ totalCount() }})</h6>
              </div>
              <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      <th>Value</th>
                      <th>Type</th>
                      <th>Documents</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (entity of entities(); track entity.value + entity.entity_type) {
                      <tr>
                        <td class="fw-semibold">{{ entity.value }}</td>
                        <td>
                          <span
                            class="badge"
                            [style.background]="getTypeColor(entity.entity_type)"
                            [style.color]="getContrastColor(getTypeColor(entity.entity_type))"
                          >
                            {{ getTypeLabel(entity.entity_type) }}
                          </span>
                        </td>
                        <td>
                          <span class="badge bg-secondary">{{ entity.document_count }}</span>
                        </td>
                        <td class="text-end">
                          <button
                            class="btn btn-sm btn-outline-primary"
                            (click)="viewEntityDocuments(entity)"
                          >
                            <i class="bi bi-eye me-1"></i>View Documents
                          </button>
                        </td>
                      </tr>
                    } @empty {
                      <tr>
                        <td colspan="4" class="text-center text-muted py-4">
                          No entities found matching the current filters.
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Pagination -->
            @if (totalCount() > pageSize) {
              <nav class="d-flex justify-content-center mt-3">
                <ul class="pagination">
                  <li class="page-item" [class.disabled]="currentPage() === 1">
                    <button class="page-link" (click)="goToPage(currentPage() - 1)">&laquo;</button>
                  </li>
                  @for (p of pageNumbers(); track p) {
                    <li class="page-item" [class.active]="p === currentPage()">
                      <button class="page-link" (click)="goToPage(p)">{{ p }}</button>
                    </li>
                  }
                  <li class="page-item" [class.disabled]="currentPage() >= totalPages()">
                    <button class="page-link" (click)="goToPage(currentPage() + 1)">&raquo;</button>
                  </li>
                </ul>
              </nav>
            }
          } @else {
            <!-- Entity Documents View -->
            <div class="card">
              <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                  <button class="btn btn-sm btn-outline-secondary me-2" (click)="clearSelection()">
                    <i class="bi bi-arrow-left"></i>
                  </button>
                  Documents containing
                  <span
                    class="badge ms-1"
                    [style.background]="getTypeColor(selectedEntity()!.entity_type)"
                    [style.color]="getContrastColor(getTypeColor(selectedEntity()!.entity_type))"
                  >
                    {{ selectedEntity()!.entity_type }}
                  </span>
                  <strong class="ms-1">{{ selectedEntity()!.value }}</strong>
                </div>
              </div>
              <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      <th>Document ID</th>
                      <th>Title</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (doc of entityDocuments(); track doc.document_id) {
                      <tr>
                        <td>#{{ doc.document_id }}</td>
                        <td>{{ doc.title }}</td>
                        <td class="text-end">
                          <a [routerLink]="['/documents', doc.document_id]" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-file-earmark-text me-1"></i>Open
                          </a>
                        </td>
                      </tr>
                    } @empty {
                      <tr>
                        <td colspan="3" class="text-center text-muted py-4">No documents found.</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class EntityBrowserComponent implements OnInit {
  entityTypes = signal<EntityType[]>([]);
  entities = signal<EntityAggregate[]>([]);
  loading = signal(true);
  totalCount = signal(0);
  currentPage = signal(1);
  selectedTypes = signal(new Set<string>());
  selectedEntity = signal<EntityAggregate | null>(null);
  entityDocuments = signal<{ document_id: number; title: string }[]>([]);

  searchQuery = '';
  pageSize = 25;

  private typeMap: Record<string, EntityType> = {};

  constructor(private entityService: EntityService) {}

  ngOnInit(): void {
    this.loadEntityTypes();
    this.loadEntities();
  }

  loadEntityTypes(): void {
    this.entityService.getEntityTypes().subscribe({
      next: (resp) => {
        this.entityTypes.set(resp.results);
        this.typeMap = {};
        for (const et of resp.results) {
          this.typeMap[et.name] = et;
        }
      },
    });
  }

  loadEntities(): void {
    this.loading.set(true);
    const types = Array.from(this.selectedTypes());
    const params: Record<string, string | number> = {
      page: this.currentPage(),
      page_size: this.pageSize,
    };
    if (types.length === 1) {
      params['entity_type'] = types[0];
    }
    if (this.searchQuery.trim()) {
      params['search'] = this.searchQuery.trim();
    }

    this.entityService.getEntities(params as Record<string, string>).subscribe({
      next: (resp) => {
        let results = resp.results;
        // Client-side filtering when multiple types selected
        if (types.length > 1) {
          results = results.filter((e) => types.includes(e.entity_type));
        }
        this.entities.set(results);
        this.totalCount.set(resp.count);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  toggleType(typeName: string): void {
    const types = new Set(this.selectedTypes());
    if (types.has(typeName)) {
      types.delete(typeName);
    } else {
      types.add(typeName);
    }
    this.selectedTypes.set(types);
    this.currentPage.set(1);
    this.loadEntities();
  }

  getTypeColor(typeName: string): string {
    return this.typeMap[typeName]?.color || '#6c757d';
  }

  getTypeLabel(typeName: string): string {
    return this.typeMap[typeName]?.label || typeName;
  }

  getContrastColor(hexColor: string): string {
    if (!hexColor || !hexColor.startsWith('#')) return '#ffffff';
    const r = parseInt(hexColor.slice(1, 3), 16);
    const g = parseInt(hexColor.slice(3, 5), 16);
    const b = parseInt(hexColor.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#000000' : '#ffffff';
  }

  viewEntityDocuments(entity: EntityAggregate): void {
    this.selectedEntity.set(entity);
    this.entityService
      .getEntityDocuments(entity.entity_type, entity.value)
      .subscribe({
        next: (docs) => this.entityDocuments.set(docs),
      });
  }

  clearSelection(): void {
    this.selectedEntity.set(null);
    this.entityDocuments.set([]);
  }

  totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize);
  }

  pageNumbers(): number[] {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadEntities();
  }
}
