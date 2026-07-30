import { Component, Input, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AIService } from '../../services/ai.service';
import { SemanticSearchResult } from '../../models/ai.model';

@Component({
  selector: 'app-similar-documents',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="sd">
      <div class="sd__head">
        <span class="dv-eyebrow">similar documents</span>
      </div>

      @if (loading()) {
        <div class="dv-empty sd__empty">
          <span class="dv-spinner"></span>
          <span class="dv-sr">Loading similar documents…</span>
        </div>
      } @else if (results().length === 0) {
        <div class="dv-empty sd__empty">No similar documents found.</div>
      } @else {
        @for (doc of results(); track doc.id) {
          <a
            class="dv-card dv-card--r9 dv-card--hover sd__row"
            [routerLink]="['/documents', doc.id]"
          >
            <span class="sd__main">
              <span class="sd__title dv-clip">{{ doc.title }}</span>
              @if (doc.correspondent || doc.document_type) {
                <span class="dv-meta sd__sub dv-clip">
                  @if (doc.correspondent) {
                    {{ doc.correspondent }}
                  }
                  @if (doc.correspondent && doc.document_type) {
                    ·
                  }
                  @if (doc.document_type) {
                    {{ doc.document_type }}
                  }
                </span>
              }
            </span>
            <span class="dv-meta sd__score" title="Similarity score">{{
              doc.score | number: '1.2-2'
            }}</span>
          </a>
        }
      }
    </div>
  `,
  styleUrl: './similar-documents.component.scss',
})
export class SimilarDocumentsComponent implements OnInit {
  @Input() documentId!: number;

  results = signal<SemanticSearchResult[]>([]);
  loading = signal(false);

  constructor(private aiService: AIService) {}

  ngOnInit() {
    this.loading.set(true);
    this.aiService.similarDocuments(this.documentId, 5).subscribe({
      next: (res) => {
        this.results.set(res.results);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
