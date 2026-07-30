import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PhysicalRecordService } from '../../services/physical-record.service';
import { PhysicalLocation } from '../../models/physical-record.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-physical-locations',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, SubnavComponent],
  styleUrl: './physical-locations.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-section pl-section">
          <span class="dv-eyebrow">physical locations</span>
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--md dv-push"
            (click)="showForm = true; resetForm()"
          >
            + Add location
          </button>
        </div>

        <!-- Create / edit form -->
        @if (showForm) {
          <div class="dv-card dv-card--pad pl-form">
            <div class="dv-card__title pl-form__title">
              {{ editingId ? 'Edit' : 'Add' }} location
            </div>

            <div class="pl-grid">
              <label class="pl-field">
                <span class="dv-field__label">name</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  placeholder="Location name"
                  [(ngModel)]="formData.name"
                />
              </label>

              <label class="pl-field">
                <span class="dv-field__label">type</span>
                <select class="dv-select dv-input--r7" [(ngModel)]="formData.location_type">
                  <option value="building">building</option>
                  <option value="room">room</option>
                  <option value="cabinet">cabinet</option>
                  <option value="shelf">shelf</option>
                  <option value="box">box</option>
                </select>
              </label>

              <label class="pl-field">
                <span class="dv-field__label">parent</span>
                <select class="dv-select dv-input--r7" [(ngModel)]="formData.parent">
                  <option [ngValue]="null">— no parent —</option>
                  @for (loc of flatLocations(); track loc.id) {
                    <option [ngValue]="loc.id">{{ loc.name }} ({{ loc.location_type }})</option>
                  }
                </select>
              </label>

              <label class="pl-field">
                <span class="dv-field__label">capacity</span>
                <input
                  type="number"
                  class="dv-input dv-input--r7 dv-mono"
                  placeholder="Max items"
                  [(ngModel)]="formData.capacity"
                />
              </label>

              <label class="pl-field">
                <span class="dv-field__label">barcode</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7 dv-mono"
                  placeholder="optional"
                  [(ngModel)]="formData.barcode"
                />
              </label>

              <label class="pl-field pl-field--full">
                <span class="dv-field__label">notes</span>
                <input
                  type="text"
                  class="dv-input dv-input--r7"
                  placeholder="optional"
                  [(ngModel)]="formData.notes"
                />
              </label>
            </div>

            <div class="pl-form__actions">
              <button
                type="button"
                class="dv-btn dv-btn--primary dv-btn--md"
                (click)="saveLocation()"
              >
                {{ editingId ? 'Update' : 'Create' }}
              </button>
              <button type="button" class="dv-btn dv-btn--ghost dv-btn--md" (click)="showForm = false">
                Cancel
              </button>
            </div>
          </div>
        }

        @if (loading()) {
          <div class="dv-empty"><span class="dv-spinner"></span> Loading…</div>
        } @else if (tree().length === 0) {
          <div class="dv-empty">
            No physical locations configured. Add your first location to start tracking physical
            records.
          </div>
        } @else {
          <div class="pl-tree">
            @for (item of flatTree(); track item.location.id) {
              <div
                class="dv-row dv-row--static dv-row--tight pl-row"
                [class.pl-row--off]="!item.location.is_active"
                [style.margin-left.px]="item.depth * 24"
              >
                @if (item.location.children_count > 0) {
                  <button
                    type="button"
                    class="pl-twisty"
                    [attr.aria-expanded]="expandedIds().has(item.location.id)"
                    [attr.aria-label]="
                      (expandedIds().has(item.location.id) ? 'Collapse ' : 'Expand ') +
                      item.location.name
                    "
                    (click)="toggleExpand(item.location.id)"
                  >
                    {{ expandedIds().has(item.location.id) ? '▾' : '▸' }}
                  </button>
                } @else {
                  <span class="pl-twisty" aria-hidden="true"></span>
                }

                <span class="dv-meta pl-kind">{{ typeLabel(item.location.location_type) }}</span>
                <span class="pl-name">{{ item.location.name }}</span>

                @if (item.location.barcode) {
                  <span class="dv-chip dv-chip--well">{{ item.location.barcode }}</span>
                }
                @if (!item.location.is_active) {
                  <span class="dv-chip dv-chip--upper">inactive</span>
                }

                <span class="dv-push pl-count dv-mono">
                  @if (item.location.capacity) {
                    {{ item.location.current_count }}/{{ item.location.capacity }}
                  } @else {
                    {{ item.location.current_count }}
                  }
                </span>

                @if (item.location.capacity) {
                  <span class="dv-bar dv-bar--sm pl-bar">
                    <span
                      class="dv-bar__fill"
                      [ngClass]="getCapacityBarClass(item.location)"
                      [style.width.%]="getCapacityPercent(item.location)"
                    ></span>
                  </span>
                }

                <span class="pl-actions">
                  <button
                    type="button"
                    class="dv-rowaction dv-rowaction--accent pl-action"
                    title="Edit"
                    (click)="editLocation(item.location)"
                  >
                    edit
                  </button>
                  <button
                    type="button"
                    class="dv-rowaction dv-rowaction--accent pl-action"
                    [title]="item.location.is_active ? 'Deactivate' : 'Activate'"
                    (click)="toggleActive(item.location)"
                  >
                    {{ item.location.is_active ? 'hide' : 'show' }}
                  </button>
                  <button
                    type="button"
                    class="dv-rowaction dv-rowaction--accent pl-action"
                    title="Add child location"
                    (click)="addChild(item.location)"
                  >
                    + child
                  </button>
                </span>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class PhysicalLocationsComponent implements OnInit {
  tree = signal<PhysicalLocation[]>([]);
  flatLocations = signal<PhysicalLocation[]>([]);
  loading = signal(false);
  expandedIds = signal<Set<number>>(new Set());
  showForm = false;
  editingId: number | null = null;

  formData: Partial<PhysicalLocation> = {
    name: '',
    location_type: 'building',
    parent: null,
    barcode: null,
    capacity: null,
    notes: '',
  };

  constructor(private physicalRecordService: PhysicalRecordService) {}

  ngOnInit(): void {
    this.loadTree();
  }

  loadTree(): void {
    this.loading.set(true);
    this.physicalRecordService.getLocationTree().subscribe({
      next: (data) => {
        this.tree.set(data);
        this.flatLocations.set(this.flattenTree(data));
        // Auto-expand root nodes
        const ids = new Set<number>();
        data.forEach((node) => ids.add(node.id));
        this.expandedIds.set(ids);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  private flattenTree(nodes: PhysicalLocation[]): PhysicalLocation[] {
    const result: PhysicalLocation[] = [];
    const flatten = (list: PhysicalLocation[]) => {
      for (const node of list) {
        result.push(node);
        if (node.children && node.children.length > 0) {
          flatten(node.children);
        }
      }
    };
    flatten(nodes);
    return result;
  }

  flatTree(): { location: PhysicalLocation; depth: number }[] {
    const result: { location: PhysicalLocation; depth: number }[] = [];
    const expanded = this.expandedIds();

    const walk = (nodes: PhysicalLocation[], depth: number) => {
      for (const node of nodes) {
        result.push({ location: node, depth });
        if (
          expanded.has(node.id) &&
          node.children &&
          node.children.length > 0
        ) {
          walk(node.children, depth + 1);
        }
      }
    };

    walk(this.tree(), 0);
    return result;
  }

  toggleExpand(id: number): void {
    const ids = new Set(this.expandedIds());
    if (ids.has(id)) {
      ids.delete(id);
    } else {
      ids.add(id);
    }
    this.expandedIds.set(ids);
  }

  /** Mono kind label, as the location tree in the design uses instead of icons. */
  typeLabel(type: string): string {
    switch (type) {
      case 'building':
        return 'bldg';
      case 'cabinet':
        return 'cab';
      default:
        return type;
    }
  }

  getCapacityPercent(location: PhysicalLocation): number {
    if (!location.capacity || location.capacity === 0) return 0;
    return Math.min(100, (location.current_count / location.capacity) * 100);
  }

  /** Console meter fill modifier for how full a location is. */
  getCapacityBarClass(location: PhysicalLocation): string {
    const pct = this.getCapacityPercent(location);
    if (pct >= 90) return 'dv-bar__fill--danger';
    if (pct >= 70) return 'dv-bar__fill--warn';
    return 'dv-bar__fill--ok';
  }

  resetForm(): void {
    this.editingId = null;
    this.formData = {
      name: '',
      location_type: 'building',
      parent: null,
      barcode: null,
      capacity: null,
      notes: '',
    };
  }

  editLocation(location: PhysicalLocation): void {
    this.editingId = location.id;
    this.formData = {
      name: location.name,
      location_type: location.location_type,
      parent: location.parent,
      barcode: location.barcode,
      capacity: location.capacity,
      notes: location.notes,
    };
    this.showForm = true;
  }

  addChild(parentLocation: PhysicalLocation): void {
    this.resetForm();
    this.formData.parent = parentLocation.id;
    // Suggest next level type
    const typeOrder = ['building', 'room', 'cabinet', 'shelf', 'box'];
    const currentIdx = typeOrder.indexOf(parentLocation.location_type);
    if (currentIdx >= 0 && currentIdx < typeOrder.length - 1) {
      this.formData.location_type = typeOrder[currentIdx + 1];
    }
    this.showForm = true;
  }

  saveLocation(): void {
    if (this.editingId) {
      this.physicalRecordService
        .updateLocation(this.editingId, this.formData)
        .subscribe({
          next: () => {
            this.showForm = false;
            this.loadTree();
          },
        });
    } else {
      this.physicalRecordService.createLocation(this.formData).subscribe({
        next: () => {
          this.showForm = false;
          this.loadTree();
        },
      });
    }
  }

  toggleActive(location: PhysicalLocation): void {
    this.physicalRecordService
      .updateLocation(location.id, { is_active: !location.is_active })
      .subscribe({
        next: () => this.loadTree(),
      });
  }
}
