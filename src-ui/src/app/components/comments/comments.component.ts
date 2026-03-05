import { Component, Input, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CollaborationService } from '../../services/collaboration.service';
import { AuthService } from '../../services/auth.service';
import { Comment } from '../../models/collaboration.model';

@Component({
  selector: 'app-comments',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './comments.component.html',
})
export class CommentsComponent implements OnInit {
  @Input({ required: true }) documentId!: number;

  comments = signal<Comment[]>([]);
  loading = signal(false);
  newCommentText = signal('');
  editingComment = signal<Comment | null>(null);
  editText = signal('');
  submitting = signal(false);

  constructor(
    private collaborationService: CollaborationService,
    private authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.loadComments();
  }

  loadComments(): void {
    this.loading.set(true);
    this.collaborationService.getComments(this.documentId).subscribe({
      next: (comments) => {
        this.comments.set(comments);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  addComment(): void {
    const text = this.newCommentText().trim();
    if (!text) return;

    this.submitting.set(true);
    this.collaborationService.addComment(this.documentId, text).subscribe({
      next: () => {
        this.newCommentText.set('');
        this.submitting.set(false);
        this.loadComments();
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }

  startEdit(comment: Comment): void {
    this.editingComment.set(comment);
    this.editText.set(comment.text);
  }

  cancelEdit(): void {
    this.editingComment.set(null);
    this.editText.set('');
  }

  saveEdit(): void {
    const comment = this.editingComment();
    if (!comment) return;

    const text = this.editText().trim();
    if (!text) return;

    this.submitting.set(true);
    this.collaborationService.updateComment(this.documentId, comment.id, text).subscribe({
      next: () => {
        this.cancelEdit();
        this.submitting.set(false);
        this.loadComments();
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }

  deleteComment(comment: Comment): void {
    if (!confirm('Delete this comment?')) return;
    this.collaborationService.deleteComment(this.documentId, comment.id).subscribe({
      next: () => this.loadComments(),
    });
  }

  isOwnComment(comment: Comment): boolean {
    const user = this.authService.currentUser();
    return user !== null && user.id === comment.user;
  }

  formatTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return 'just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }
}
