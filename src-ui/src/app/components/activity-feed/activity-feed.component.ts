import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CollaborationService } from '../../services/collaboration.service';
import { ActivityEntry } from '../../models/collaboration.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-activity-feed',
  standalone: true,
  imports: [CommonModule, RouterModule, SubnavComponent],
  templateUrl: './activity-feed.component.html',
  styleUrl: './activity-feed.component.scss',
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

  /** Timeline dot colour by event class. */
  getEventDotClass(eventType: string): string {
    if (eventType.startsWith('document.') || eventType.startsWith('comment.'))
      return 'dv-dot--accent';
    if (eventType.startsWith('share.')) return 'dv-dot--ok';
    if (eventType.startsWith('checkout.') || eventType.startsWith('workflow.'))
      return 'dv-dot--warn';
    if (eventType.startsWith('retention.')) return 'dv-dot--danger';
    return '';
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
