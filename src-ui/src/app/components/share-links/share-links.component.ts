import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CollaborationService } from '../../services/collaboration.service';
import { ShareLink } from '../../models/collaboration.model';
import { SubnavComponent } from '../subnav/subnav.component';

@Component({
  selector: 'app-share-links',
  standalone: true,
  imports: [CommonModule, RouterModule, SubnavComponent],
  templateUrl: './share-links.component.html',
  styleUrl: './share-links.component.scss',
})
export class ShareLinksComponent implements OnInit {
  shareLinks = signal<ShareLink[]>([]);
  loading = signal(false);

  constructor(private collaborationService: CollaborationService) {}

  ngOnInit(): void {
    this.loadShareLinks();
  }

  loadShareLinks(): void {
    this.loading.set(true);
    this.collaborationService.getShareLinks().subscribe({
      next: (links) => {
        this.shareLinks.set(links);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  revokeLink(link: ShareLink): void {
    if (!confirm(`Revoke share link for "${link.document_title}"?`)) return;
    this.collaborationService.deleteShareLink(link.id).subscribe({
      next: () => this.loadShareLinks(),
    });
  }

  getShareUrl(slug: string): string {
    return `${window.location.origin}/share/${slug}`;
  }

  copyToClipboard(slug: string): void {
    const url = this.getShareUrl(slug);
    navigator.clipboard.writeText(url);
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  /** Compact numeric day, so the mono table columns stay narrow. */
  formatDay(dateString: string): string {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  }

  formatExpiration(expiration: string | null, isExpired: boolean): string {
    if (!expiration) return 'never';
    if (isExpired) return 'expired';
    return this.formatDay(expiration);
  }

  /** Expired links read as danger; "never" recedes to faint. */
  expiryClass(link: ShareLink): string {
    if (link.is_expired) return 'dv-danger';
    if (!link.expiration) return 'dv-faint';
    return 'dv-muted';
  }
}
