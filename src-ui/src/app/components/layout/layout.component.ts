import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { SearchService } from '../../services/search.service';
import { NotificationService } from '../../services/notification.service';
import {
  PreferencesService,
  UserPreferences,
} from '../../services/preferences.service';
import { SavedViewListItem } from '../../models/search.model';

export type ThemeMode = 'light' | 'dark' | 'system';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './layout.component.html',
  styleUrl: './layout.component.scss',
})
export class LayoutComponent implements OnInit, OnDestroy {
  sidebarCollapsed = false;
  searchQuery = signal('');
  sidebarViews = signal<SavedViewListItem[]>([]);
  unreadCount = signal(0);
  currentTheme = signal<ThemeMode>('system');

  // Sidebar section collapse state
  sectionState: Record<string, boolean> = {};

  private readonly SECTION_STATE_KEY = 'dv_sidebar_sections';

  private pollSubscription: Subscription | null = null;
  private mediaQuery: MediaQueryList | null = null;
  private mediaListener: ((e: MediaQueryListEvent) => void) | null = null;

  constructor(
    public auth: AuthService,
    private router: Router,
    private searchService: SearchService,
    private notificationService: NotificationService,
    private preferencesService: PreferencesService,
  ) {}

  ngOnInit(): void {
    this.loadSectionState();
    this.auth.getProfile().subscribe();
    this.loadSidebarViews();
    this.loadUnreadCount();
    this.loadTheme();
    this.pollSubscription = interval(30000).subscribe(() => {
      this.loadUnreadCount();
    });
  }

  ngOnDestroy(): void {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
    }
    if (this.mediaQuery && this.mediaListener) {
      this.mediaQuery.removeEventListener('change', this.mediaListener);
    }
  }

  // --- Theme ---

  loadTheme(): void {
    this.preferencesService.getPreferences().subscribe({
      next: (prefs: UserPreferences) => {
        const theme = prefs.theme as ThemeMode;
        if (theme && ['light', 'dark', 'system'].includes(theme)) {
          this.currentTheme.set(theme);
        }
        this.applyTheme();
      },
      error: () => {
        this.applyTheme();
      },
    });
  }

  setTheme(theme: ThemeMode): void {
    this.currentTheme.set(theme);
    this.applyTheme();
    this.preferencesService.updatePreferences({ theme }).subscribe();
  }

  private applyTheme(): void {
    const mode = this.currentTheme();
    if (mode === 'system') {
      this.setupSystemThemeListener();
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute(
        'data-bs-theme',
        prefersDark ? 'dark' : 'light',
      );
    } else {
      this.removeSystemThemeListener();
      document.documentElement.setAttribute('data-bs-theme', mode);
    }
  }

  private setupSystemThemeListener(): void {
    if (this.mediaQuery && this.mediaListener) return;
    this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.mediaListener = (e: MediaQueryListEvent) => {
      if (this.currentTheme() === 'system') {
        document.documentElement.setAttribute(
          'data-bs-theme',
          e.matches ? 'dark' : 'light',
        );
      }
    };
    this.mediaQuery.addEventListener('change', this.mediaListener);
  }

  private removeSystemThemeListener(): void {
    if (this.mediaQuery && this.mediaListener) {
      this.mediaQuery.removeEventListener('change', this.mediaListener);
      this.mediaQuery = null;
      this.mediaListener = null;
    }
  }

  getThemeIcon(): string {
    switch (this.currentTheme()) {
      case 'light':
        return 'bi-sun-fill';
      case 'dark':
        return 'bi-moon-fill';
      default:
        return 'bi-circle-half';
    }
  }

  // --- Existing functionality ---

  loadUnreadCount(): void {
    this.notificationService.getUnreadCount().subscribe({
      next: (resp) => this.unreadCount.set(resp.count),
    });
  }

  loadSidebarViews(): void {
    this.searchService.getSidebarViews().subscribe({
      next: (views) => this.sidebarViews.set(views),
    });
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  onSearch(): void {
    const q = this.searchQuery().trim();
    if (q) {
      this.router.navigate(['/search'], { queryParams: { q, page: 1 } });
    }
  }

  onLogout(): void {
    this.auth.logout().subscribe();
  }

  // --- Sidebar Sections ---

  isSectionOpen(section: string): boolean {
    return this.sectionState[section] !== false;
  }

  toggleSection(section: string): void {
    this.sectionState[section] = !this.isSectionOpen(section);
    this.saveSectionState();
  }

  private loadSectionState(): void {
    try {
      const stored = localStorage.getItem(this.SECTION_STATE_KEY);
      if (stored) {
        this.sectionState = JSON.parse(stored);
      }
    } catch {
      this.sectionState = {};
    }
  }

  private saveSectionState(): void {
    localStorage.setItem(this.SECTION_STATE_KEY, JSON.stringify(this.sectionState));
  }
}
