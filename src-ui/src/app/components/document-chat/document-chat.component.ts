import { Component, Input, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AIService } from '../../services/ai.service';
import { ChatMessage, ChatSource } from '../../models/ai.model';

@Component({
  selector: 'app-document-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="ch">
      <div class="ch__head">
        <span class="dv-eyebrow">ask this document</span>
        @if (messages().length > 0) {
          <button type="button" class="dv-link dv-push ch__clear" (click)="clearChat()">
            clear
          </button>
        }
      </div>

      <div class="ch__log">
        @if (messages().length === 0 && !loading()) {
          <div class="dv-empty ch__empty">Ask a question about this document.</div>
        }

        @for (msg of messages(); track $index) {
          @if (msg.role === 'user') {
            <div class="dv-card dv-card--r9 ch__turn">
              <div class="dv-meta ch__who">you</div>
              <div class="ch__body">{{ msg.content }}</div>
            </div>
          } @else {
            <div class="dv-callout ch__turn">
              <div class="dv-callout__label ch__who">docvault ai</div>
              <div class="ch__body">{{ msg.content }}</div>
            </div>
          }
        }

        @if (loading()) {
          <div class="ch__thinking">
            <span class="dv-spinner"></span>
            <span class="dv-meta">thinking…</span>
          </div>
        }
      </div>

      @if (sources().length > 0) {
        <div class="ch__cites">
          <span class="dv-eyebrow">cited</span>
          @for (source of sources(); track source.document_id) {
            <span
              class="ch__cite"
              [title]="
                source.chunk_count
                  ? source.chunk_count + ' passage(s) referenced'
                  : 'referenced'
              "
              >[{{ source.title }}]</span
            >
          }
        </div>
      }

      <div class="ch__compose">
        <input
          type="text"
          class="dv-input dv-input--r7"
          [(ngModel)]="question"
          placeholder="Ask about this document…"
          aria-label="Ask about this document"
          (keyup.enter)="send()"
          [disabled]="loading()"
        />
        <button
          type="button"
          class="dv-btn dv-btn--primary ch__ask"
          (click)="send()"
          [disabled]="loading() || !question.trim()"
        >
          Ask
        </button>
      </div>
    </div>
  `,
  styleUrl: './document-chat.component.scss',
})
export class DocumentChatComponent {
  @Input() documentId!: number;

  question = '';
  messages = signal<ChatMessage[]>([]);
  sources = signal<ChatSource[]>([]);
  loading = signal(false);

  constructor(private aiService: AIService) {}

  send() {
    const q = this.question.trim();
    if (!q) return;

    this.messages.update(msgs => [...msgs, { role: 'user', content: q }]);
    this.question = '';
    this.loading.set(true);

    this.aiService.chatWithDocument(this.documentId, {
      question: q,
      history: this.messages(),
    }).subscribe({
      next: (res) => {
        this.messages.update(msgs => [...msgs, { role: 'assistant', content: res.answer }]);
        this.sources.set(res.sources);
        this.loading.set(false);
      },
      error: () => {
        this.messages.update(msgs => [...msgs, { role: 'assistant', content: 'An error occurred. Please try again.' }]);
        this.loading.set(false);
      },
    });
  }

  clearChat() {
    this.messages.set([]);
    this.sources.set([]);
  }
}
