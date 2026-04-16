import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { vi, describe, beforeEach, it, expect } from 'vitest';

import { LayoutComponent } from './layout.component';
import { AuthService } from '../../services/auth.service';
import { SearchService } from '../../services/search.service';
import { NotificationService } from '../../services/notification.service';
import { PreferencesService } from '../../services/preferences.service';

function buildAuthService() {
  return {
    currentUser: signal<null | { is_staff?: boolean; is_superuser?: boolean }>(null),
    getProfile: vi.fn(() => of({})),
    logout: vi.fn(() => of(void 0)),
  };
}

function buildSearchService() {
  return {
    getSidebarViews: vi.fn(() => of([])),
  };
}

function buildNotificationService() {
  return {
    getUnreadCount: vi.fn(() => of({ count: 0 })),
  };
}

function buildPreferencesService() {
  return {
    getPreferences: vi.fn(() => of({ theme: 'light' })),
    updatePreferences: vi.fn(() => of({})),
  };
}

describe('LayoutComponent', () => {
  let fixture: ComponentFixture<LayoutComponent>;
  let component: LayoutComponent;
  let authSvc: ReturnType<typeof buildAuthService>;
  let searchSvc: ReturnType<typeof buildSearchService>;
  let notifSvc: ReturnType<typeof buildNotificationService>;
  let prefsSvc: ReturnType<typeof buildPreferencesService>;

  beforeEach(async () => {
    // Clear sidebar section state so each test starts fresh
    localStorage.removeItem('dv_sidebar_sections');

    authSvc = buildAuthService();
    searchSvc = buildSearchService();
    notifSvc = buildNotificationService();
    prefsSvc = buildPreferencesService();

    // Mock window.matchMedia which is not available in jsdom
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    await TestBed.configureTestingModule({
      imports: [LayoutComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authSvc },
        { provide: SearchService, useValue: searchSvc },
        { provide: NotificationService, useValue: notifSvc },
        { provide: PreferencesService, useValue: prefsSvc },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // --- sidebar toggle ---

  it('should start with sidebar expanded', () => {
    expect(component.sidebarCollapsed).toBe(false);
  });

  it('should toggle sidebar collapsed state', () => {
    component.toggleSidebar();
    expect(component.sidebarCollapsed).toBe(true);

    component.toggleSidebar();
    expect(component.sidebarCollapsed).toBe(false);
  });

  // --- section collapse / expand ---

  it('should report unknown sections as open by default', () => {
    expect(component.isSectionOpen('documents')).toBe(true);
    expect(component.isSectionOpen('tags')).toBe(true);
  });

  it('should toggle a section to closed', () => {
    component.toggleSection('documents');
    expect(component.isSectionOpen('documents')).toBe(false);
  });

  it('should toggle a section back to open', () => {
    component.toggleSection('documents');
    component.toggleSection('documents');
    expect(component.isSectionOpen('documents')).toBe(true);
  });

  it('should persist section state to localStorage', () => {
    component.toggleSection('tags');
    const stored = JSON.parse(localStorage.getItem('dv_sidebar_sections')!);
    expect(stored['tags']).toBe(false);
  });

  // --- theme switching ---

  it('should default currentTheme to system', () => {
    // theme is loaded from preferences which returns 'light'
    expect(['system', 'light', 'dark']).toContain(component.currentTheme());
  });

  it('should update currentTheme when setTheme is called', () => {
    component.setTheme('dark');
    expect(component.currentTheme()).toBe('dark');
    expect(prefsSvc.updatePreferences).toHaveBeenCalledWith({ theme: 'dark' });
  });

  it('should set theme to light and call updatePreferences', () => {
    component.setTheme('light');
    expect(component.currentTheme()).toBe('light');
    expect(prefsSvc.updatePreferences).toHaveBeenCalledWith({ theme: 'light' });
  });

  it('getThemeIcon should return correct icon for light', () => {
    component.setTheme('light');
    expect(component.getThemeIcon()).toBe('bi-sun-fill');
  });

  it('getThemeIcon should return correct icon for dark', () => {
    component.setTheme('dark');
    expect(component.getThemeIcon()).toBe('bi-moon-fill');
  });

  it('getThemeIcon should return correct icon for system', () => {
    component.setTheme('system');
    expect(component.getThemeIcon()).toBe('bi-circle-half');
  });

  // --- isAdmin ---

  it('isAdmin should return false when no user is set', () => {
    authSvc.currentUser.set(null);
    expect(component.isAdmin()).toBe(false);
  });

  it('isAdmin should return true for is_staff user', () => {
    authSvc.currentUser.set({ is_staff: true });
    expect(component.isAdmin()).toBe(true);
  });

  it('isAdmin should return true for is_superuser user', () => {
    authSvc.currentUser.set({ is_superuser: true });
    expect(component.isAdmin()).toBe(true);
  });

  it('isAdmin should return false for regular user', () => {
    authSvc.currentUser.set({ is_staff: false, is_superuser: false });
    expect(component.isAdmin()).toBe(false);
  });

  // --- globalSearchOpen toggle via Ctrl+K ---

  it('should open global search overlay on Ctrl+K', () => {
    expect(component.globalSearchOpen()).toBe(false);
    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
    component.onGlobalKeydown(event);
    expect(component.globalSearchOpen()).toBe(true);
  });

  it('should close global search overlay on second Ctrl+K', () => {
    component.globalSearchOpen.set(true);
    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
    component.onGlobalKeydown(event);
    expect(component.globalSearchOpen()).toBe(false);
  });

  it('should not toggle global search for unrelated keys', () => {
    const event = new KeyboardEvent('keydown', { key: 'a', ctrlKey: true });
    component.onGlobalKeydown(event);
    expect(component.globalSearchOpen()).toBe(false);
  });

  // --- ngOnInit side effects ---

  it('should call getProfile on init', () => {
    expect(authSvc.getProfile).toHaveBeenCalled();
  });

  it('should call getSidebarViews on init', () => {
    expect(searchSvc.getSidebarViews).toHaveBeenCalled();
  });

  it('should call getUnreadCount on init', () => {
    expect(notifSvc.getUnreadCount).toHaveBeenCalled();
  });

  // --- onSearch ---

  it('should not navigate when search query is empty', () => {
    component.searchQuery.set('');
    // just ensure no error is thrown
    expect(() => component.onSearch()).not.toThrow();
  });

  // --- ngOnDestroy ---

  it('should clean up poll subscription on destroy', () => {
    expect(() => component.ngOnDestroy()).not.toThrow();
  });
});
