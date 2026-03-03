import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AIService } from '../../services/ai.service';
import { AIConfig } from '../../models/ai.model';

@Component({
  selector: 'app-ai-config',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container-fluid py-4">
      <h4>AI Configuration</h4>

      @if (config(); as cfg) {
        <div class="row mt-3">
          <div class="col-md-6">
            <div class="card">
              <div class="card-header">LLM Provider</div>
              <div class="card-body">
                <table class="table table-sm mb-0">
                  <tbody>
                    <tr><td>Enabled</td><td>
                      <span class="badge" [class]="cfg.llm_enabled ? 'bg-success' : 'bg-secondary'">
                        {{ cfg.llm_enabled ? 'Yes' : 'No' }}
                      </span>
                    </td></tr>
                    <tr><td>Provider</td><td>{{ cfg.llm_provider }}</td></tr>
                    <tr><td>Model</td><td>{{ cfg.llm_model }}</td></tr>
                    <tr><td>Embedding Model</td><td>{{ cfg.embedding_model }}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="card">
              <div class="card-header">Vector Store</div>
              <div class="card-body">
                <p class="mb-2">Documents indexed: <strong>{{ cfg.vector_store_count }}</strong></p>
                <button class="btn btn-warning btn-sm" (click)="rebuildIndex()" [disabled]="rebuilding()">
                  @if (rebuilding()) {
                    <span class="spinner-border spinner-border-sm me-1"></span>
                  }
                  Rebuild Vector Index
                </button>
                @if (rebuildMessage()) {
                  <div class="alert alert-info mt-2 mb-0">{{ rebuildMessage() }}</div>
                }
              </div>
            </div>
          </div>
        </div>
      } @else {
        <div class="text-center py-4">
          <div class="spinner-border"></div>
        </div>
      }
    </div>
  `,
})
export class AIConfigComponent implements OnInit {
  config = signal<AIConfig | null>(null);
  rebuilding = signal(false);
  rebuildMessage = signal('');

  constructor(private aiService: AIService) {}

  ngOnInit() {
    this.aiService.getConfig().subscribe(cfg => this.config.set(cfg));
  }

  rebuildIndex() {
    this.rebuilding.set(true);
    this.rebuildMessage.set('');
    this.aiService.rebuildIndex().subscribe({
      next: (res) => {
        this.rebuildMessage.set(res.message);
        this.rebuilding.set(false);
      },
      error: () => {
        this.rebuildMessage.set('Failed to start rebuild.');
        this.rebuilding.set(false);
      },
    });
  }
}
