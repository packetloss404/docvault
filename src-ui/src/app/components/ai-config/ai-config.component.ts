import { Component, OnInit, signal } from '@angular/core';
import { AIService } from '../../services/ai.service';
import { AIConfig } from '../../models/ai.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-ai-config',
  standalone: true,
  imports: [SubnavComponent],
  styleUrl: './ai-config.component.scss',
  template: `
    <div class="dv-screen dv-screen--tight">
      <div class="dv-inner dv-inner--wide">
        <dv-subnav />

        <div class="dv-pagehead pagehead">
          <h1 class="dv-h1 dv-h1--sm">AI configuration</h1>
        </div>

        @if (config(); as cfg) {
          <div class="card-grid">
            <!-- LLM provider -->
            <div class="dv-card dv-card--pad">
              <div class="card-head">
                <span class="dv-card__title">LLM provider</span>
                <span class="state dv-push" [class.state--on]="cfg.llm_enabled">
                  {{ cfg.llm_enabled ? '● enabled' : '○ disabled' }}
                </span>
              </div>

              <div class="chips">
                <span class="dv-navchip is-active">{{ cfg.llm_provider || 'unset' }}</span>
              </div>

              <div class="stat-lines">
                <div class="dv-stat-line">
                  <span class="dv-stat-line__k">chat model</span>
                  <span class="dv-stat-line__v">{{ cfg.llm_model || '—' }}</span>
                </div>
                <div class="dv-stat-line">
                  <span class="dv-stat-line__k">embeddings</span>
                  <span class="dv-stat-line__v">{{ cfg.embedding_model || '—' }}</span>
                </div>
              </div>

              @if (isLocalProvider()) {
                <div class="card-note dv-meta">runs fully local — no data leaves your server</div>
              }
            </div>

            <!-- Vector store -->
            <div class="dv-card dv-card--pad">
              <div class="card-head">
                <span class="dv-card__title">Vector store</span>
              </div>

              <div class="stat-lines">
                <div class="dv-stat-line">
                  <span class="dv-stat-line__k">documents indexed</span>
                  <span class="dv-stat-line__v dv-accent">{{ cfg.vector_store_count }}</span>
                </div>
              </div>

              <button
                type="button"
                class="dv-btn dv-btn--secondary dv-btn--sm store-action"
                (click)="rebuildIndex()"
                [disabled]="rebuilding()"
              >
                @if (rebuilding()) {
                  <span class="dv-spinner"></span>
                  Rebuilding…
                } @else {
                  Rebuild vector index
                }
              </button>

              @if (rebuildMessage()) {
                <div class="notice card-note" role="status">{{ rebuildMessage() }}</div>
              }
            </div>
          </div>
        } @else {
          <div class="dv-empty">
            <span class="dv-spinner"></span>
            <div class="load-label">Loading AI configuration…</div>
          </div>
        }
      </div>
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

  /** Local inference backends keep every request on this server. */
  isLocalProvider(): boolean {
    const provider = (this.config()?.llm_provider ?? '').toLowerCase();
    return provider === 'ollama' || provider === 'local' || provider === 'llamacpp';
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
