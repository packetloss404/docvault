import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { NotificationService } from '../../services/notification.service';
import { Notification } from '../../models/notification.model';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './notifications.component.html',
})
export class NotificationsComponent implements OnInit {
  notifications = signal<Notification[]>([]);
  showUnreadOnly = signal(false);
  loading = signal(false);

  constructor(private notificationService: NotificationService) {}

  ngOnInit(): void {
    this.loadNotifications();
  }

  loadNotifications(): void {
    this.loading.set(true);
    const unread = this.showUnreadOnly() ? true : undefined;
    this.notificationService.getNotifications(unread).subscribe({
      next: (resp) => {
        this.notifications.set(resp.results);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  toggleFilter(): void {
    this.showUnreadOnly.set(!this.showUnreadOnly());
    this.loadNotifications();
  }

  markRead(notification: Notification): void {
    if (notification.read) {
      return;
    }
    this.notificationService.markRead(notification.id).subscribe({
      next: () => {
        this.notifications.set(
          this.notifications().map((n) =>
            n.id === notification.id ? { ...n, read: true } : n,
          ),
        );
      },
    });
  }

  markAllRead(): void {
    this.notificationService.markAllRead().subscribe({
      next: () => {
        this.notifications.set(
          this.notifications().map((n) => ({ ...n, read: true })),
        );
      },
    });
  }

  getEventBadgeClass(eventType: string): string {
    if (eventType.startsWith('document.')) {
      return 'bg-primary';
    }
    if (eventType.startsWith('workflow.')) {
      return 'bg-info text-dark';
    }
    if (eventType.startsWith('quota.')) {
      return 'bg-warning text-dark';
    }
    if (eventType.startsWith('retention.')) {
      return 'bg-danger';
    }
    return 'bg-secondary';
  }

  truncateBody(body: string, maxLength: number = 80): string {
    if (body.length <= maxLength) {
      return body;
    }
    return body.substring(0, maxLength) + '...';
  }

  formatTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) {
      return 'just now';
    }
    if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    }
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) {
      return `${diffHours}h ago`;
    }
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) {
      return `${diffDays}d ago`;
    }
    return date.toLocaleDateString();
  }
}
