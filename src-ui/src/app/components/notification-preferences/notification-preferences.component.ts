import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { NotificationService } from '../../services/notification.service';
import { NotificationPreference, QuotaUsage } from '../../models/notification.model';

interface PreferenceRow {
  event_type: string;
  in_app: NotificationPreference | null;
  email: NotificationPreference | null;
  webhook: NotificationPreference | null;
}

const EVENT_TYPES = [
  'document.added',
  'document.updated',
  'document.deleted',
  'document.processing_complete',
  'document.processing_failed',
  'workflow.transition',
  'workflow.completed',
  'quota.warning',
  'quota.exceeded',
  'retention.expiring',
  'retention.deleted',
];

const CHANNELS: Array<'in_app' | 'email' | 'webhook'> = ['in_app', 'email', 'webhook'];

@Component({
  selector: 'app-notification-preferences',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './notification-preferences.component.html',
})
export class NotificationPreferencesComponent implements OnInit {
  preferences = signal<NotificationPreference[]>([]);
  rows = signal<PreferenceRow[]>([]);
  quotaUsage = signal<QuotaUsage | null>(null);
  saving = signal(false);
  webhookUrls = signal<Record<string, string>>({});

  readonly eventTypes = EVENT_TYPES;
  readonly channels = CHANNELS;

  constructor(private notificationService: NotificationService) {}

  ngOnInit(): void {
    this.loadPreferences();
    this.loadQuotaUsage();
  }

  loadPreferences(): void {
    this.notificationService.getPreferences().subscribe({
      next: (resp) => {
        this.preferences.set(resp.results);
        this.buildRows(resp.results);
      },
    });
  }

  loadQuotaUsage(): void {
    this.notificationService.getQuotaUsage().subscribe({
      next: (usage) => this.quotaUsage.set(usage),
    });
  }

  buildRows(prefs: NotificationPreference[]): void {
    const urls: Record<string, string> = {};
    const builtRows = EVENT_TYPES.map((eventType) => {
      const row: PreferenceRow = {
        event_type: eventType,
        in_app: null,
        email: null,
        webhook: null,
      };
      for (const pref of prefs) {
        if (pref.event_type === eventType) {
          row[pref.channel] = pref;
          if (pref.channel === 'webhook' && pref.webhook_url) {
            urls[eventType] = pref.webhook_url;
          }
        }
      }
      return row;
    });
    this.rows.set(builtRows);
    this.webhookUrls.set(urls);
  }

  isEnabled(row: PreferenceRow, channel: 'in_app' | 'email' | 'webhook'): boolean {
    const pref = row[channel];
    return pref !== null && pref.enabled;
  }

  togglePreference(row: PreferenceRow, channel: 'in_app' | 'email' | 'webhook'): void {
    const pref = row[channel];
    if (pref) {
      // Update existing preference
      this.notificationService
        .updatePreference(pref.id, { enabled: !pref.enabled })
        .subscribe({
          next: () => this.loadPreferences(),
        });
    } else {
      // Create new preference
      this.notificationService
        .createPreference({
          event_type: row.event_type,
          channel: channel,
          enabled: true,
          webhook_url: channel === 'webhook' ? '' : '',
        })
        .subscribe({
          next: () => this.loadPreferences(),
        });
    }
  }

  getWebhookUrl(eventType: string): string {
    return this.webhookUrls()[eventType] || '';
  }

  setWebhookUrl(eventType: string, url: string): void {
    this.webhookUrls.set({ ...this.webhookUrls(), [eventType]: url });
  }

  saveWebhookUrl(row: PreferenceRow): void {
    const pref = row.webhook;
    const url = this.webhookUrls()[row.event_type] || '';
    if (pref) {
      this.saving.set(true);
      this.notificationService
        .updatePreference(pref.id, { webhook_url: url })
        .subscribe({
          next: () => {
            this.saving.set(false);
            this.loadPreferences();
          },
          error: () => this.saving.set(false),
        });
    }
  }

  formatEventType(eventType: string): string {
    return eventType
      .split('.')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' / ')
      .replace(/_/g, ' ');
  }

  formatChannelLabel(channel: string): string {
    switch (channel) {
      case 'in_app':
        return 'In-App';
      case 'email':
        return 'Email';
      case 'webhook':
        return 'Webhook';
      default:
        return channel;
    }
  }

  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i];
  }

  getUsagePercent(used: number, max: number | null): number {
    if (max === null || max === 0) return 0;
    return Math.min(100, Math.round((used / max) * 100));
  }

  getProgressBarClass(percent: number): string {
    if (percent >= 90) return 'bg-danger';
    if (percent >= 75) return 'bg-warning';
    return 'bg-success';
  }
}
