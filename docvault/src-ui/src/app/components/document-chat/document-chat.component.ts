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
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0">Document Chat</h6>
        <button class="btn btn-sm btn-outline-secondary" (click)="clearChat()">Clear</button>
      </div>
      <div class="card-body" style="max-height: 400px; overflow-y: auto;">
        @if (messages().length === 0) {
          <p class="text-muted text-center">Ask a question about this document...</p>
        }
        @for (msg of messages(); track $index) {
          <div class="mb-2" [class]="msg.role === 'user' ? 'text-end' : ''">
            <div class="d-inline-block p-2 rounded" [class]="msg.role === 'user' ? 'bg-primary text-white' : 'bg-light'">
              {{ msg.content }}
            </div>
          </div>
        }
        @if (loading()) {
          <div class="text-center">
            <div class="spinner-border spinner-border-sm text-primary"></div>
            <span class="ms-2 text-muted">Thinking...</span>
          </div>
        }
      </div>
      <div class="card-footer">
        @if (sources().length > 0) {
          <div class="mb-2">
            <small class="text-muted">Sources: {{ sources().length }} chunk(s) referenced</small>
          </div>
        }
        <div class="input-group">
          <input type="text" class="form-control" [(ngModel)]="question"
                 placeholder="Ask a question..." (keyup.enter)="send()"
                 [disabled]="loading()">
          <button class="btn btn-primary" (click)="send()" [disabled]="loading() || !question.trim()">
            Send
          </button>
        </div>
      </div>
    </div>
  `,
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
