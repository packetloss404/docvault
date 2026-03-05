import {
  Component,
  Input,
  OnInit,
  OnChanges,
  SimpleChanges,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MlService } from '../../services/ml.service';
import { SuggestionItem } from '../../models/ml.model';

interface DisplaySuggestion {
  category: 'tags' | 'correspondent' | 'document_type' | 'storage_path';
  item: SuggestionItem;
}

@Component({
  selector: 'app-suggestion-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './suggestion-panel.component.html',
})
export class SuggestionPanelComponent implements OnInit, OnChanges {
  @Input({ required: true }) documentId!: number;

  tags = signal<SuggestionItem[]>([]);
  correspondent = signal<SuggestionItem[]>([]);
  documentType = signal<SuggestionItem[]>([]);
  storagePath = signal<SuggestionItem[]>([]);

  loading = signal(false);
  error = signal<string | null>(null);
  applyingAll = signal(false);

  constructor(private mlService: MlService) {}

  ngOnInit(): void {
    this.loadSuggestions();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['documentId'] && !changes['documentId'].firstChange) {
      this.loadSuggestions();
    }
  }

  loadSuggestions(): void {
    if (!this.documentId) return;

    this.loading.set(true);
    this.error.set(null);

    this.mlService.getSuggestions(this.documentId).subscribe({
      next: (suggestions) => {
        this.tags.set(suggestions.tags);
        this.correspondent.set(suggestions.correspondent);
        this.documentType.set(suggestions.document_type);
        this.storagePath.set(suggestions.storage_path);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(
          err.status === 404
            ? 'No suggestions available'
            : 'Failed to load suggestions',
        );
        this.loading.set(false);
      },
    });
  }

  get hasSuggestions(): boolean {
    return (
      this.tags().length > 0 ||
      this.correspondent().length > 0 ||
      this.documentType().length > 0 ||
      this.storagePath().length > 0
    );
  }

  get allSuggestions(): DisplaySuggestion[] {
    const result: DisplaySuggestion[] = [];
    for (const item of this.tags()) {
      result.push({ category: 'tags', item });
    }
    for (const item of this.correspondent()) {
      result.push({ category: 'correspondent', item });
    }
    for (const item of this.documentType()) {
      result.push({ category: 'document_type', item });
    }
    for (const item of this.storagePath()) {
      result.push({ category: 'storage_path', item });
    }
    return result;
  }

  confidencePercent(confidence: number): string {
    return `${Math.round(confidence * 100)}%`;
  }

  confidenceClass(confidence: number): string {
    if (confidence >= 0.8) return 'bg-success';
    if (confidence >= 0.5) return 'bg-warning text-dark';
    return 'bg-secondary';
  }

  confidenceBorderClass(confidence: number): string {
    if (confidence >= 0.8) return 'border-success';
    if (confidence >= 0.5) return 'border-warning';
    return 'border-secondary';
  }

  categoryLabel(category: string): string {
    switch (category) {
      case 'tags':
        return 'Tag';
      case 'correspondent':
        return 'Correspondent';
      case 'document_type':
        return 'Document Type';
      case 'storage_path':
        return 'Storage Path';
      default:
        return category;
    }
  }

  categoryIcon(category: string): string {
    switch (category) {
      case 'tags':
        return 'bi-tag';
      case 'correspondent':
        return 'bi-person';
      case 'document_type':
        return 'bi-file-earmark';
      case 'storage_path':
        return 'bi-folder2';
      default:
        return 'bi-question-circle';
    }
  }

  acceptSuggestion(category: string, item: SuggestionItem): void {
    switch (category) {
      case 'tags':
        this.mlService.applyTag(this.documentId, item.id).subscribe({
          next: () => this.removeSuggestion('tags', item.id),
        });
        break;
      case 'correspondent':
        this.mlService
          .applyCorrespondent(this.documentId, item.id)
          .subscribe({
            next: () => this.removeSuggestion('correspondent', item.id),
          });
        break;
      case 'document_type':
        this.mlService
          .applyDocumentType(this.documentId, item.id)
          .subscribe({
            next: () => this.removeSuggestion('document_type', item.id),
          });
        break;
      case 'storage_path':
        this.mlService
          .applyStoragePath(this.documentId, item.id)
          .subscribe({
            next: () => this.removeSuggestion('storage_path', item.id),
          });
        break;
    }
  }

  dismissSuggestion(category: string, itemId: number): void {
    this.removeSuggestion(category, itemId);
  }

  acceptAll(): void {
    this.applyingAll.set(true);
    const all = this.allSuggestions;
    let remaining = all.length;

    if (remaining === 0) {
      this.applyingAll.set(false);
      return;
    }

    const onComplete = () => {
      remaining--;
      if (remaining <= 0) {
        this.applyingAll.set(false);
      }
    };

    for (const suggestion of all) {
      switch (suggestion.category) {
        case 'tags':
          this.mlService
            .applyTag(this.documentId, suggestion.item.id)
            .subscribe({
              next: () => {
                this.removeSuggestion('tags', suggestion.item.id);
                onComplete();
              },
              error: () => onComplete(),
            });
          break;
        case 'correspondent':
          this.mlService
            .applyCorrespondent(this.documentId, suggestion.item.id)
            .subscribe({
              next: () => {
                this.removeSuggestion('correspondent', suggestion.item.id);
                onComplete();
              },
              error: () => onComplete(),
            });
          break;
        case 'document_type':
          this.mlService
            .applyDocumentType(this.documentId, suggestion.item.id)
            .subscribe({
              next: () => {
                this.removeSuggestion('document_type', suggestion.item.id);
                onComplete();
              },
              error: () => onComplete(),
            });
          break;
        case 'storage_path':
          this.mlService
            .applyStoragePath(this.documentId, suggestion.item.id)
            .subscribe({
              next: () => {
                this.removeSuggestion('storage_path', suggestion.item.id);
                onComplete();
              },
              error: () => onComplete(),
            });
          break;
      }
    }
  }

  private removeSuggestion(category: string, itemId: number): void {
    switch (category) {
      case 'tags':
        this.tags.update((items) => items.filter((i) => i.id !== itemId));
        break;
      case 'correspondent':
        this.correspondent.update((items) =>
          items.filter((i) => i.id !== itemId),
        );
        break;
      case 'document_type':
        this.documentType.update((items) =>
          items.filter((i) => i.id !== itemId),
        );
        break;
      case 'storage_path':
        this.storagePath.update((items) =>
          items.filter((i) => i.id !== itemId),
        );
        break;
    }
  }
}
