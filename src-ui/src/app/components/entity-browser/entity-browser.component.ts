import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { EntityService } from '../../services/entity.service';
import { EntityAggregate, EntityCooccurrence, EntityType } from '../../models/entity.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-entity-browser',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <!-- Kind filter chips -->
        <div class="dv-navchips eb-kinds">
          <button
            type="button"
            class="dv-navchip"
            [class.is-active]="selectedTypes().size === 0"
            (click)="clearTypes()"
          >
            all
          </button>
          @for (et of entityTypes(); track et.id) {
            <button
              type="button"
              class="dv-navchip"
              [class.is-active]="selectedTypes().has(et.name)"
              [attr.aria-pressed]="selectedTypes().has(et.name)"
              (click)="toggleType(et.name)"
            >
              {{ et.label || et.name }}
            </button>
          }
        </div>

        <div class="eb-search">
          <input
            type="text"
            class="dv-input dv-input--r7"
            [(ngModel)]="searchQuery"
            (keyup.enter)="loadEntities()"
            placeholder="Filter by value…"
            aria-label="Filter entities by value"
          />
          <button type="button" class="dv-btn dv-btn--ghost dv-btn--sm" (click)="loadEntities()">
            Search
          </button>
        </div>

        @if (loading()) {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <span class="dv-sr">Loading…</span>
          </div>
        } @else if (!selectedEntity()) {
          <div class="dv-section eb-section">
            <span class="dv-eyebrow">{{ totalCount() }} entities</span>
          </div>

          <div class="dv-thead dv-grid" style="--dv-cols: 90px minmax(0,1fr) 110px 110px">
            <span>kind</span>
            <span>value</span>
            <span class="dv-num">docs</span>
            <span></span>
          </div>

          @for (entity of entities(); track entity.value + entity.entity_type) {
            <div
              class="dv-row dv-grid eb-row"
              style="--dv-cols: 90px minmax(0,1fr) 110px 110px"
              role="button"
              tabindex="0"
              (click)="viewEntityDocuments(entity)"
              (keyup.enter)="viewEntityDocuments(entity)"
            >
              <span
                class="dv-chip dv-chip--upper eb-kind"
                [class.dv-chip--accent]="chipToneFor(entity.entity_type) === 'accent'"
                [class.dv-chip--warn]="chipToneFor(entity.entity_type) === 'warn'"
                [class.dv-chip--ok]="chipToneFor(entity.entity_type) === 'ok'"
                >{{ getTypeLabel(entity.entity_type) }}</span
              >
              <span class="dv-clip eb-value">{{ entity.value }}</span>
              <span class="dv-mono dv-num dv-muted">{{ entity.document_count }} docs</span>
              <span class="dv-meta dv-num">documents →</span>
            </div>
          } @empty {
            <div class="dv-empty">No entities found matching the current filters.</div>
          }

          @if (totalCount() > pageSize) {
            <nav class="dv-pager" aria-label="Entity pages">
              <span
                [class.is-disabled]="currentPage() === 1"
                (click)="goToPage(currentPage() - 1)"
                >prev</span
              >
              @for (p of pageNumbers(); track p) {
                <span [class.is-current]="p === currentPage()" (click)="goToPage(p)">{{ p }}</span>
              }
              <span
                [class.is-disabled]="currentPage() >= totalPages()"
                (click)="goToPage(currentPage() + 1)"
                >next</span
              >
            </nav>
          }
        } @else {
          <!-- Entity detail -->
          <div class="dv-crumb eb-crumb">
            <button
              type="button"
              class="dv-crumb__up"
              aria-label="Back to entities"
              (click)="clearSelection()"
            >
              ←
            </button>
            <span>documents containing</span>
            <span
              class="dv-chip dv-chip--upper"
              [class.dv-chip--accent]="chipToneFor(selectedEntity()!.entity_type) === 'accent'"
              [class.dv-chip--warn]="chipToneFor(selectedEntity()!.entity_type) === 'warn'"
              [class.dv-chip--ok]="chipToneFor(selectedEntity()!.entity_type) === 'ok'"
              >{{ getTypeLabel(selectedEntity()!.entity_type) }}</span
            >
            <span class="eb-value">{{ selectedEntity()!.value }}</span>
          </div>

          <div class="dv-thead dv-grid" style="--dv-cols: 90px minmax(0,1fr) 90px">
            <span>doc id</span>
            <span>title</span>
            <span class="dv-num">open</span>
          </div>

          @for (doc of entityDocuments(); track doc.document_id) {
            <a
              class="dv-row dv-grid"
              style="--dv-cols: 90px minmax(0,1fr) 90px"
              [routerLink]="['/documents', doc.document_id]"
            >
              <span class="dv-mono dv-faint">#{{ doc.document_id }}</span>
              <span class="dv-clip eb-value">{{ doc.title }}</span>
              <span class="dv-meta dv-num dv-accent">open →</span>
            </a>
          } @empty {
            <div class="dv-empty">No documents found.</div>
          }

          @if (cooccurrence().length > 0) {
            <div class="dv-section eb-section">
              <span class="dv-card__title">Co-occurring entities</span>
            </div>
            <div class="eb-cooc">
              @for (
                item of cooccurrence();
                track item.entity.value + item.entity.entity_type
              ) {
                <div class="dv-card dv-card--r9 eb-cooc__item">
                  <span
                    class="dv-chip dv-chip--upper"
                    [class.dv-chip--accent]="chipToneFor(item.entity.entity_type) === 'accent'"
                    [class.dv-chip--warn]="chipToneFor(item.entity.entity_type) === 'warn'"
                    [class.dv-chip--ok]="chipToneFor(item.entity.entity_type) === 'ok'"
                    >{{ getTypeLabel(item.entity.entity_type) }}</span
                  >
                  <span class="dv-clip eb-value">{{ item.entity.value }}</span>
                  <span class="dv-meta dv-push">×{{ item.count }}</span>
                </div>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        display: contents;
      }

      dv-subnav {
        display: block;
        margin-bottom: 16px;
      }

      .eb-kinds {
        margin-bottom: 12px;
      }

      .eb-search {
        display: flex;
        gap: 8px;
        align-items: center;
        max-width: 420px;
        margin-bottom: 14px;

        .dv-input {
          flex: 1;
          min-width: 0;
        }
      }

      .eb-section {
        align-items: center;
      }

      .eb-row {
        cursor: pointer;
      }

      .eb-kind {
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .eb-value {
        font-size: 13.5px;
        font-weight: 500;
        color: var(--text);
      }

      .eb-crumb {
        padding: 0 0 12px;
        border-bottom: none;
        flex-wrap: wrap;
      }

      .eb-cooc {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 10px;

        &__item {
          display: flex;
          align-items: center;
          gap: 9px;
          padding: 10px 13px;
          min-width: 0;
        }
      }

      .dv-pager .is-disabled {
        opacity: 0.4;
        cursor: default;
      }
    `,
  ],
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
  cooccurrence = signal<EntityCooccurrence[]>([]);

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

  /** Clears the kind filter — the "all" chip. */
  clearTypes(): void {
    if (this.selectedTypes().size === 0) return;
    this.selectedTypes.set(new Set<string>());
    this.currentPage.set(1);
    this.loadEntities();
  }

  getTypeLabel(typeName: string): string {
    return this.typeMap[typeName]?.label || typeName;
  }

  /**
   * Console tone for an entity kind. The backend stores a free-form hex colour
   * per entity type, but the design system only allows tokens, so kinds map onto
   * the status/accent tones instead: orgs accent, people warn, amounts ok,
   * everything else neutral.
   */
  chipToneFor(typeName: string): 'accent' | 'warn' | 'ok' | 'neutral' {
    const name = (typeName || '').toLowerCase();
    if (name.includes('org') || name.includes('company')) return 'accent';
    if (name.includes('person') || name.includes('people') || name.includes('name')) {
      return 'warn';
    }
    if (
      name.includes('money') ||
      name.includes('amount') ||
      name.includes('currency') ||
      name.includes('total')
    ) {
      return 'ok';
    }
    return 'neutral';
  }

  viewEntityDocuments(entity: EntityAggregate): void {
    this.selectedEntity.set(entity);
    this.cooccurrence.set([]);
    this.entityService
      .getEntityDocuments(entity.entity_type, entity.value)
      .subscribe({
        next: (docs) => this.entityDocuments.set(docs),
      });
    this.entityService.getCooccurrence(entity.entity_type, entity.value).subscribe({
        next: (items) => this.cooccurrence.set(items),
        error: () => this.cooccurrence.set([]),
    });
  }

  clearSelection(): void {
    this.selectedEntity.set(null);
    this.entityDocuments.set([]);
    this.cooccurrence.set([]);
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
