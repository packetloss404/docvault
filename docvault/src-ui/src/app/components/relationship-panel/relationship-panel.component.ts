import { Component, Input, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { RelationshipService } from '../../services/relationship.service';
import {
  DocumentRelationship,
  RelationshipType,
} from '../../models/relationship.model';

@Component({
  selector: 'app-relationship-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="container-fluid py-3">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="mb-0">
          <i class="bi bi-diagram-2 me-2"></i>Document Relationships
        </h4>
        <a
          *ngIf="resolvedDocumentId"
          [routerLink]="['/documents', resolvedDocumentId, 'graph']"
          class="btn btn-outline-primary btn-sm"
        >
          <i class="bi bi-share me-1"></i>View Graph
        </a>
      </div>

      <!-- Add Relationship Form -->
      <div class="card mb-4">
        <div class="card-header">
          <i class="bi bi-plus-circle me-1"></i>Add Relationship
        </div>
        <div class="card-body">
          <div class="row g-2 align-items-end">
            <div class="col-md-3">
              <label class="form-label">Target Document ID</label>
              <input
                type="number"
                class="form-control form-control-sm"
                placeholder="Document ID"
                [ngModel]="newTargetId()"
                (ngModelChange)="newTargetId.set($event)"
              />
            </div>
            <div class="col-md-3">
              <label class="form-label">Relationship Type</label>
              <select
                class="form-select form-select-sm"
                [ngModel]="newTypeId()"
                (ngModelChange)="newTypeId.set($event)"
              >
                <option [ngValue]="0" disabled>Select type...</option>
                @for (t of relationshipTypes(); track t.id) {
                  <option [ngValue]="t.id">
                    {{ t.label }}
                  </option>
                }
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Notes</label>
              <input
                type="text"
                class="form-control form-control-sm"
                placeholder="Optional notes"
                [ngModel]="newNotes()"
                (ngModelChange)="newNotes.set($event)"
              />
            </div>
            <div class="col-md-2">
              <button
                class="btn btn-primary btn-sm w-100"
                (click)="addRelationship()"
                [disabled]="!newTargetId() || !newTypeId()"
              >
                <i class="bi bi-plus me-1"></i>Add
              </button>
            </div>
          </div>
          @if (addError()) {
            <div class="alert alert-danger mt-2 mb-0 py-1 small">
              {{ addError() }}
            </div>
          }
        </div>
      </div>

      <!-- Relationships List grouped by type -->
      @if (loading()) {
        <div class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      } @else if (relationships().length === 0) {
        <div class="text-center text-muted py-4">
          <i class="bi bi-diagram-2 fs-1"></i>
          <p class="mt-2">No relationships found for this document.</p>
        </div>
      } @else {
        @for (group of groupedRelationships(); track group.typeLabel) {
          <div class="card mb-3">
            <div class="card-header py-2">
              <i class="bi" [ngClass]="group.typeIcon || 'bi-link-45deg'"></i>
              <strong class="ms-1">{{ group.typeLabel }}</strong>
              <span class="badge bg-secondary ms-2">{{
                group.items.length
              }}</span>
            </div>
            <ul class="list-group list-group-flush">
              @for (rel of group.items; track rel.id) {
                <li
                  class="list-group-item d-flex justify-content-between align-items-center"
                >
                  <div>
                    <a
                      [routerLink]="[
                        '/documents',
                        rel.source_document === resolvedDocumentId
                          ? rel.target_document
                          : rel.source_document
                      ]"
                      class="text-decoration-none"
                    >
                      <i class="bi bi-file-earmark me-1"></i>
                      {{
                        rel.source_document === resolvedDocumentId
                          ? rel.target_title
                          : rel.source_title
                      }}
                    </a>
                    <small class="text-muted ms-2">
                      (ID:
                      {{
                        rel.source_document === resolvedDocumentId
                          ? rel.target_document
                          : rel.source_document
                      }})
                    </small>
                    @if (rel.notes) {
                      <br /><small class="text-muted">{{ rel.notes }}</small>
                    }
                  </div>
                  <button
                    class="btn btn-outline-danger btn-sm"
                    (click)="deleteRelationship(rel.id)"
                    title="Remove relationship"
                  >
                    <i class="bi bi-trash"></i>
                  </button>
                </li>
              }
            </ul>
          </div>
        }
      }
    </div>
  `,
})
export class RelationshipPanelComponent implements OnInit {
  @Input() documentId: number | null = null;

  resolvedDocumentId: number = 0;
  relationships = signal<DocumentRelationship[]>([]);
  relationshipTypes = signal<RelationshipType[]>([]);
  loading = signal(true);

  newTargetId = signal<number>(0);
  newTypeId = signal<number>(0);
  newNotes = signal('');
  addError = signal('');

  groupedRelationships = signal<
    { typeLabel: string; typeIcon: string; items: DocumentRelationship[] }[]
  >([]);

  constructor(
    private relationshipService: RelationshipService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    if (this.documentId) {
      this.resolvedDocumentId = this.documentId;
    } else {
      this.resolvedDocumentId = Number(this.route.snapshot.paramMap.get('id'));
    }
    this.loadRelationshipTypes();
    this.loadRelationships();
  }

  loadRelationshipTypes(): void {
    this.relationshipService.getRelationshipTypes().subscribe({
      next: (types) => this.relationshipTypes.set(types),
    });
  }

  loadRelationships(): void {
    this.loading.set(true);
    this.relationshipService
      .getDocumentRelationships(this.resolvedDocumentId)
      .subscribe({
        next: (rels) => {
          this.relationships.set(rels);
          this.buildGroups(rels);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  private buildGroups(rels: DocumentRelationship[]): void {
    const map = new Map<
      string,
      { typeLabel: string; typeIcon: string; items: DocumentRelationship[] }
    >();
    for (const rel of rels) {
      const key = rel.relationship_type_label;
      if (!map.has(key)) {
        map.set(key, {
          typeLabel: key,
          typeIcon: rel.relationship_type_icon,
          items: [],
        });
      }
      map.get(key)!.items.push(rel);
    }
    this.groupedRelationships.set(Array.from(map.values()));
  }

  addRelationship(): void {
    this.addError.set('');
    const data = {
      target_document: this.newTargetId(),
      relationship_type: this.newTypeId(),
      notes: this.newNotes(),
    };
    this.relationshipService
      .createDocumentRelationship(this.resolvedDocumentId, data)
      .subscribe({
        next: () => {
          this.newTargetId.set(0);
          this.newTypeId.set(0);
          this.newNotes.set('');
          this.loadRelationships();
        },
        error: (err) => {
          this.addError.set(
            err.error?.detail || 'Failed to create relationship.',
          );
        },
      });
  }

  deleteRelationship(relId: number): void {
    if (!confirm('Remove this relationship?')) return;
    this.relationshipService
      .deleteDocumentRelationship(this.resolvedDocumentId, relId)
      .subscribe({
        next: () => this.loadRelationships(),
      });
  }
}
