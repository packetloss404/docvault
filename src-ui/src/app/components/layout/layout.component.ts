import {
  Component,
  HostListener,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  NavigationEnd,
  Event as RouterEvent,
  Router,
  RouterModule,
} from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { Subscription, filter, interval, map, startWith } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { NotificationService } from '../../services/notification.service';
import { ShellStatsService } from '../../services/shell-stats.service';
import { ThemeService } from '../../services/theme.service';
import { UploadService } from '../../services/upload.service';
import { GlobalSearchOverlayComponent } from '../global-search-overlay/global-search-overlay.component';
import { IconComponent } from '../icon/icon.component';
import { RAIL, RailItem, isUnder } from '../../nav';

const STATS_POLL_MS = 30000;

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [RouterModule, GlobalSearchOverlayComponent, IconComponent],
  templateUrl: './layout.component.html',
  styleUrl: './layout.component.scss',
})
export class LayoutComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  readonly theme = inject(ThemeService);
  readonly stats = inject(ShellStatsService);
  readonly uploads = inject(UploadService);
  private readonly router = inject(Router);
  private readonly notifications = inject(NotificationService);

  readonly unreadCount = signal(0);
  readonly paletteOpen = signal(false);

  private pollSubscription: Subscription | null = null;

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((e: RouterEvent): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  readonly isStaff = computed(() => {
    const user = this.auth.currentUser();
    return !!(user?.is_staff || user?.is_superuser);
  });

  readonly railItems = computed(() =>
    RAIL.filter((item) => !item.staffOnly || this.isStaff()),
  );

  readonly initials = computed(() => {
    const source = this.auth.currentUser()?.username ?? '';
    if (!source) return '··';
    const parts = source.split(/[\s._-]+/).filter(Boolean);
    const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : source.slice(0, 2);
    return letters.toLowerCase();
  });

  readonly themeTitle = computed(
    () => `Theme: ${this.theme.mode()} — click to change`,
  );

  ngOnInit(): void {
    this.auth.getProfile().subscribe({
      next: () => this.stats.refresh(this.isStaff()),
      error: () => this.stats.refresh(false),
    });
    this.theme.load();
    this.loadUnreadCount();
    this.pollSubscription = interval(STATS_POLL_MS).subscribe(() => {
      this.loadUnreadCount();
      this.stats.refresh(this.isStaff());
    });
  }

  ngOnDestroy(): void {
    this.pollSubscription?.unsubscribe();
  }

  isActive(item: RailItem): boolean {
    return item.match.some((prefix) => isUnder(this.url(), prefix));
  }

  @HostListener('document:keydown', ['$event'])
  onGlobalKeydown(event: KeyboardEvent): void {
    if (event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      this.paletteOpen.update((open) => !open);
      return;
    }
    if (event.key === 'Escape' && this.paletteOpen()) {
      this.paletteOpen.set(false);
      return;
    }
    // Shift+U uploads — but not while the user is typing into a field.
    if (
      event.key === 'U' &&
      event.shiftKey &&
      !event.ctrlKey &&
      !event.metaKey &&
      !isTypingTarget(event.target)
    ) {
      event.preventDefault();
      this.uploads.pick();
    }
  }

  // Shell-wide "drop files anywhere to ingest".
  @HostListener('document:dragover', ['$event'])
  onDragOver(event: DragEvent): void {
    if (!event.dataTransfer?.types?.includes('Files')) return;
    event.preventDefault();
    this.uploads.setDragActive(true);
  }

  @HostListener('document:dragleave', ['$event'])
  onDragLeave(event: DragEvent): void {
    // relatedTarget is null only when the pointer leaves the window entirely.
    if (event.relatedTarget === null) this.uploads.setDragActive(false);
  }

  @HostListener('document:drop', ['$event'])
  onDrop(event: DragEvent): void {
    const files = event.dataTransfer?.files;
    if (!files?.length) return;
    event.preventDefault();
    this.uploads.setDragActive(false);
    this.uploads.upload(files);
  }

  private loadUnreadCount(): void {
    this.notifications.getUnreadCount().subscribe({
      next: (resp) => this.unreadCount.set(resp.count),
      error: () => {},
    });
  }
}

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return (
    tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
  );
}
