import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CollaborationService } from '../../services/collaboration.service';
import { ActivityEntry } from '../../models/collaboration.model';

@Component({
  selector: 'app-activity-feed',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './activity-feed.component.html',
})
export class ActivityFeedComponent implements OnInit {
  activities = signal<ActivityEntry[]>([]);
  loading = signal(false);

  constructor(private collaborationService: CollaborationService) {}

  ngOnInit(): void {
    this.loadActivity();
  }

  loadActivity(): void {
    this.loading.set(true);
    this.collaborationService.getGlobalActivity().subscribe({
      next: (entries) => {
        this.activities.set(entries);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  getEventBadgeClass(eventType: string): string {
    if (eventType.startsWith('document.')) return 'bg-primary';
    if (eventType.startsWith('comment.')) return 'bg-success';
    if (eventType.startsWith('checkout.')) return 'bg-warning text-dark';
    if (eventType.startsWith('share.')) return 'bg-info text-dark';
    if (eventType.startsWith('workflow.')) return 'bg-purple';
    if (eventType.startsWith('retention.')) return 'bg-danger';
    return 'bg-secondary';
  }

  getEventIcon(eventType: string): string {
    if (eventType.startsWith('document.')) return 'bi-file-earmark-text';
    if (eventType.startsWith('comment.')) return 'bi-chat-dots';
    if (eventType.startsWith('checkout.')) return 'bi-lock';
    if (eventType.startsWith('share.')) return 'bi-link-45deg';
    if (eventType.startsWith('workflow.')) return 'bi-diagram-3';
    if (eventType.startsWith('retention.')) return 'bi-trash';
    return 'bi-circle';
  }

  truncateBody(body: string, maxLength: number = 100): string {
    if (body.length <= maxLength) return body;
    return body.substring(0, maxLength) + '...';
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
