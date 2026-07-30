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
    <div class="rp" [class.rp--screen]="!embedded">
      <div class="rp__head">
        <span class="dv-eyebrow">relationships</span>
        @if (resolvedDocumentId) {
          <a
            class="dv-link dv-mono dv-push rp__graph"
            [routerLink]="['/documents', resolvedDocumentId, 'graph']"
            >graph →</a
          >
        }
      </div>

      <!-- Add relationship -->
      <div class="dv-card dv-card--r9 rp__add">
        <div class="rp__addrow">
          <input
            type="number"
            class="dv-input dv-input--r7 rp__id"
            placeholder="doc id"
            aria-label="Target document ID"
            [ngModel]="newTargetId()"
            (ngModelChange)="newTargetId.set($event)"
          />
          <select
            class="dv-input dv-input--r7 rp__type"
            aria-label="Relationship type"
            [ngModel]="newTypeId()"
            (ngModelChange)="newTypeId.set($event)"
          >
            <option [ngValue]="0" disabled>relation…</option>
            @for (t of relationshipTypes(); track t.id) {
              <option [ngValue]="t.id">{{ t.label }}</option>
            }
          </select>
          <button
            type="button"
            class="dv-btn dv-btn--accent dv-btn--sm rp__addbtn"
            (click)="addRelationship()"
            [disabled]="!newTargetId() || !newTypeId()"
          >
            + add
          </button>
        </div>
        <input
          type="text"
          class="dv-input dv-input--r7 rp__notes"
          placeholder="Notes (optional)"
          aria-label="Relationship notes"
          [ngModel]="newNotes()"
          (ngModelChange)="newNotes.set($event)"
        />
        @if (addError()) {
          <div class="dv-danger rp__error">{{ addError() }}</div>
        }
      </div>

      <!-- Relationship rows, grouped by type -->
      @if (loading()) {
        <div class="dv-empty rp__empty">
          <span class="dv-spinner"></span>
          <span class="dv-sr">Loading relationships…</span>
        </div>
      } @else if (relationships().length === 0) {
        <div class="dv-empty rp__empty">No relationships for this document.</div>
      } @else {
        @for (group of groupedRelationships(); track group.typeLabel) {
          @for (rel of group.items; track rel.id) {
            <div class="dv-card dv-card--r9 dv-card--hover rp__row">
              <span class="dv-chip dv-chip--upper rp__kind">{{
                group.typeLabel
              }}</span>
              <a
                class="rp__title dv-clip"
                [routerLink]="[
                  '/documents',
                  rel.source_document === resolvedDocumentId
                    ? rel.target_document
                    : rel.source_document
                ]"
                [title]="rel.notes || null"
                >{{
                  rel.source_document === resolvedDocumentId
                    ? rel.target_title
                    : rel.source_title
                }}</a
              >
              <span class="dv-meta rp__date">{{
                rel.created_at | date: 'yyyy-MM-dd'
              }}</span>
              <button
                type="button"
                class="rp__del"
                title="Remove relationship"
                (click)="deleteRelationship(rel.id)"
              >
                <span aria-hidden="true">✕</span>
                <span class="dv-sr">Remove relationship</span>
              </button>
            </div>
          }
        }
      }
    </div>
  `,
  styleUrl: './relationship-panel.component.scss',
})
export class RelationshipPanelComponent implements OnInit {
  @Input() documentId: number | null = null;

  resolvedDocumentId: number = 0;
  /** True when rendered inside the document panel rather than as a screen. */
  embedded = false;
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
      this.embedded = true;
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
