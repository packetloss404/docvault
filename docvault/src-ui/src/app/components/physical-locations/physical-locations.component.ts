import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { PhysicalRecordService } from '../../services/physical-record.service';
import { PhysicalLocation } from '../../models/physical-record.model';

@Component({
  selector: 'app-physical-locations',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h3 class="mb-0">Physical Locations</h3>
      <button class="btn btn-primary" (click)="showForm = true; resetForm()">
        <i class="bi bi-plus-lg me-1"></i>Add Location
      </button>
    </div>

    <!-- Create/Edit Form -->
    @if (showForm) {
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ editingId ? 'Edit' : 'Add' }} Location</span>
          <button class="btn-close" (click)="showForm = false"></button>
        </div>
        <div class="card-body">
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Name</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="formData.name"
                placeholder="Location name"
              />
            </div>
            <div class="col-md-3">
              <label class="form-label">Type</label>
              <select class="form-select" [(ngModel)]="formData.location_type">
                <option value="building">Building</option>
                <option value="room">Room</option>
                <option value="cabinet">Cabinet</option>
                <option value="shelf">Shelf</option>
                <option value="box">Box</option>
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label">Parent</label>
              <select class="form-select" [(ngModel)]="formData.parent">
                <option [ngValue]="null">-- No Parent --</option>
                @for (loc of flatLocations(); track loc.id) {
                  <option [ngValue]="loc.id">{{ loc.name }} ({{ loc.location_type }})</option>
                }
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label">Capacity</label>
              <input
                type="number"
                class="form-control"
                [(ngModel)]="formData.capacity"
                placeholder="Max items"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">Barcode</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="formData.barcode"
                placeholder="Barcode (optional)"
              />
            </div>
            <div class="col-md-8">
              <label class="form-label">Notes</label>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="formData.notes"
                placeholder="Notes (optional)"
              />
            </div>
            <div class="col-12">
              <button class="btn btn-primary me-2" (click)="saveLocation()">
                {{ editingId ? 'Update' : 'Create' }}
              </button>
              <button class="btn btn-secondary" (click)="showForm = false">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    }

    @if (loading()) {
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    } @else if (tree().length === 0) {
      <div class="text-center text-muted py-5">
        <i class="bi bi-building fs-1"></i>
        <p class="mt-2">No physical locations configured.</p>
        <p class="small">Add your first location to start tracking physical records.</p>
      </div>
    } @else {
      <div class="card">
        <div class="card-body p-0">
          <div class="list-group list-group-flush">
            @for (node of tree(); track node.id) {
              <ng-container>
                <!-- Render tree recursively using depth-first flat list -->
              </ng-container>
            }
            @for (item of flatTree(); track item.location.id) {
              <div
                class="list-group-item d-flex justify-content-between align-items-center"
                [style.padding-left.px]="20 + item.depth * 28"
                [class.text-muted]="!item.location.is_active"
              >
                <div class="d-flex align-items-center">
                  @if (item.location.children_count > 0) {
                    <button
                      class="btn btn-sm btn-link p-0 me-2"
                      (click)="toggleExpand(item.location.id)"
                    >
                      <i
                        class="bi"
                        [ngClass]="expandedIds().has(item.location.id) ? 'bi-chevron-down' : 'bi-chevron-right'"
                      ></i>
                    </button>
                  } @else {
                    <span class="me-4"></span>
                  }
                  <i class="bi me-2" [ngClass]="getTypeIcon(item.location.location_type)"></i>
                  <span [class.text-decoration-line-through]="!item.location.is_active">
                    {{ item.location.name }}
                  </span>
                  <span class="badge bg-light text-dark ms-2">{{ item.location.location_type }}</span>
                  @if (item.location.barcode) {
                    <span class="badge bg-info text-dark ms-1">
                      <i class="bi bi-upc-scan me-1"></i>{{ item.location.barcode }}
                    </span>
                  }
                </div>
                <div class="d-flex align-items-center gap-2">
                  @if (item.location.capacity) {
                    <div style="width: 100px;">
                      <div class="progress" style="height: 8px;">
                        <div
                          class="progress-bar"
                          [ngClass]="getCapacityBarClass(item.location)"
                          role="progressbar"
                          [style.width.%]="getCapacityPercent(item.location)"
                        ></div>
                      </div>
                      <small class="text-muted">
                        {{ item.location.current_count }}/{{ item.location.capacity }}
                      </small>
                    </div>
                  }
                  <div class="btn-group btn-group-sm">
                    <button
                      class="btn btn-outline-secondary"
                      title="Edit"
                      (click)="editLocation(item.location)"
                    >
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button
                      class="btn btn-outline-secondary"
                      [title]="item.location.is_active ? 'Deactivate' : 'Activate'"
                      (click)="toggleActive(item.location)"
                    >
                      <i
                        class="bi"
                        [ngClass]="item.location.is_active ? 'bi-eye-slash' : 'bi-eye'"
                      ></i>
                    </button>
                    <button
                      class="btn btn-outline-secondary"
                      title="Add Child"
                      (click)="addChild(item.location)"
                    >
                      <i class="bi bi-plus"></i>
                    </button>
                  </div>
                </div>
              </div>
            }
          </div>
        </div>
      </div>
    }
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

  getTypeIcon(type: string): string {
    switch (type) {
      case 'building':
        return 'bi-building';
      case 'room':
        return 'bi-door-open';
      case 'cabinet':
        return 'bi-archive';
      case 'shelf':
        return 'bi-bookshelf';
      case 'box':
        return 'bi-box';
      default:
        return 'bi-geo-alt';
    }
  }

  getCapacityPercent(location: PhysicalLocation): number {
    if (!location.capacity || location.capacity === 0) return 0;
    return Math.min(100, (location.current_count / location.capacity) * 100);
  }

  getCapacityBarClass(location: PhysicalLocation): Record<string, boolean> {
    const pct = this.getCapacityPercent(location);
    return {
      'bg-success': pct < 70,
      'bg-warning': pct >= 70 && pct < 90,
      'bg-danger': pct >= 90,
    };
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
