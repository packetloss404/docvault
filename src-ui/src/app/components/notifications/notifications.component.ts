import { Component, OnInit, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { NotificationService } from '../../services/notification.service';
import { NotificationWebSocketService } from '../../services/websocket.service';
import { Notification } from '../../models/notification.model';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss',
})
export class NotificationsComponent implements OnInit {
  notifications = signal<Notification[]>([]);
  showUnreadOnly = signal(false);
  loading = signal(false);

  /** Unread rows in the current page — drives the mono readout in the head. */
  readonly unreadCount = computed(
    () => this.notifications().filter((n) => !n.read).length,
  );

  constructor(private notificationService: NotificationService, live: NotificationWebSocketService) {
    effect(() => { if (live.notification()) this.loadNotifications(); });
  }

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

  /** Console chip modifier for a category, applied alongside `.dv-chip`. */
  getEventBadgeClass(eventType: string): string {
    if (eventType.startsWith('workflow.')) {
      return 'dv-chip--accent';
    }
    if (eventType.startsWith('quota.')) {
      return 'dv-chip--warn';
    }
    if (eventType.startsWith('retention.')) {
      return 'dv-chip--danger';
    }
    return 'dv-chip--well';
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
