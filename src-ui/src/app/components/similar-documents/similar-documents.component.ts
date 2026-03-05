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
    <div class="card">
      <div class="card-header">
        <h6 class="mb-0">Similar Documents</h6>
      </div>
      <div class="card-body p-0">
        @if (loading()) {
          <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm"></div>
          </div>
        } @else if (results().length === 0) {
          <p class="text-muted text-center py-3 mb-0">No similar documents found.</p>
        } @else {
          <ul class="list-group list-group-flush">
            @for (doc of results(); track doc.id) {
              <li class="list-group-item">
                <a [routerLink]="['/documents', doc.id]" class="text-decoration-none">
                  <strong>{{ doc.title }}</strong>
                </a>
                <br>
                <small class="text-muted">
                  @if (doc.correspondent) { {{ doc.correspondent }} &middot; }
                  @if (doc.document_type) { {{ doc.document_type }} &middot; }
                  Score: {{ doc.score | number:'1.2-2' }}
                </small>
              </li>
            }
          </ul>
        }
      </div>
    </div>
  `,
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
