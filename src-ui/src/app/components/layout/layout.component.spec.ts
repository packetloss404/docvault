import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { vi, describe, beforeEach, it, expect } from 'vitest';

import { LayoutComponent } from './layout.component';
import { AuthService } from '../../services/auth.service';
import { NotificationService } from '../../services/notification.service';
import { PreferencesService } from '../../services/preferences.service';
import { ShellStatsService } from '../../services/shell-stats.service';
import { UploadService } from '../../services/upload.service';
import { RAIL } from '../../nav';

function buildAuthService() {
  return {
    currentUser: signal<null | {
      username?: string;
      is_staff?: boolean;
      is_superuser?: boolean;
    }>(null),
    getProfile: vi.fn(() => of({})),
    logout: vi.fn(() => of(void 0)),
  };
}

function buildNotificationService() {
  return { getUnreadCount: vi.fn(() => of({ count: 3 })) };
}

function buildPreferencesService() {
  return {
    getPreferences: vi.fn(() => of({ theme: 'dark' })),
    updatePreferences: vi.fn(() => of({})),
  };
}

function buildStatsService() {
  return {
    refresh: vi.fn(),
    ocrLabel: () => 'ocr idle',
    ocrBusy: () => false,
    documentsLabel: () => '12 docs',
    storageLabel: () => null,
  };
}

function buildUploadService() {
  return {
    pick: vi.fn(),
    upload: vi.fn(),
    setDragActive: vi.fn(),
    clearMessage: vi.fn(),
    uploading: () => false,
    dragActive: () => false,
    message: () => '',
    error: () => false,
  };
}

describe('LayoutComponent', () => {
  let fixture: ComponentFixture<LayoutComponent>;
  let component: LayoutComponent;
  let authSvc: ReturnType<typeof buildAuthService>;
  let notifSvc: ReturnType<typeof buildNotificationService>;
  let statsSvc: ReturnType<typeof buildStatsService>;
  let uploadSvc: ReturnType<typeof buildUploadService>;

  beforeEach(async () => {
    localStorage.clear();

    authSvc = buildAuthService();
    notifSvc = buildNotificationService();
    statsSvc = buildStatsService();
    uploadSvc = buildUploadService();

    // jsdom has no matchMedia; ThemeService needs it at construction.
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );

    await TestBed.configureTestingModule({
      imports: [LayoutComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authSvc },
        { provide: NotificationService, useValue: notifSvc },
        { provide: PreferencesService, useValue: buildPreferencesService() },
        { provide: ShellStatsService, useValue: statsSvc },
        { provide: UploadService, useValue: uploadSvc },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // --- rail ---

  it('hides staff-only rail items from regular users', () => {
    authSvc.currentUser.set({ is_staff: false, is_superuser: false });
    const keys = component.railItems().map((item) => item.key);
    expect(keys).not.toContain('admin');
    expect(keys).not.toContain('comp');
  });

  it('shows staff-only rail items to staff', () => {
    authSvc.currentUser.set({ is_staff: true });
    const keys = component.railItems().map((item) => item.key);
    expect(keys).toContain('admin');
    expect(keys).toContain('comp');
  });

  it('shows staff-only rail items to superusers', () => {
    authSvc.currentUser.set({ is_superuser: true });
    expect(component.railItems().map((i) => i.key)).toContain('admin');
  });

  it('exposes every non-staff rail item to anonymous state', () => {
    const expected = RAIL.filter((item) => !item.staffOnly).length;
    expect(component.railItems().length).toBe(expected);
  });

  it('marks the dashboard active at the root url', () => {
    const dash = RAIL.find((item) => item.key === 'dash')!;
    // The test router starts at '/'.
    expect(component.isActive(dash)).toBe(true);
  });

  it('does not mark documents active at the root url', () => {
    const docs = RAIL.find((item) => item.key === 'docs')!;
    expect(component.isActive(docs)).toBe(false);
  });

  // --- avatar initials ---

  it('falls back to a placeholder when no user is loaded', () => {
    authSvc.currentUser.set(null);
    expect(component.initials()).toBe('··');
  });

  it('derives two initials from a single-word username', () => {
    authSvc.currentUser.set({ username: 'jordan' });
    expect(component.initials()).toBe('jo');
  });

  it('derives initials across a separator', () => {
    authSvc.currentUser.set({ username: 'jordan.reed' });
    expect(component.initials()).toBe('jr');
  });

  // --- command palette ---

  it('opens the palette on Ctrl+K', () => {
    expect(component.paletteOpen()).toBe(false);
    component.onGlobalKeydown(
      new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }),
    );
    expect(component.paletteOpen()).toBe(true);
  });

  it('opens the palette on Cmd+K', () => {
    component.onGlobalKeydown(
      new KeyboardEvent('keydown', { key: 'k', metaKey: true }),
    );
    expect(component.paletteOpen()).toBe(true);
  });

  it('closes the palette on a second Ctrl+K', () => {
    component.paletteOpen.set(true);
    component.onGlobalKeydown(
      new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }),
    );
    expect(component.paletteOpen()).toBe(false);
  });

  it('closes the palette on Escape', () => {
    component.paletteOpen.set(true);
    component.onGlobalKeydown(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(component.paletteOpen()).toBe(false);
  });

  it('ignores unrelated shortcuts', () => {
    component.onGlobalKeydown(
      new KeyboardEvent('keydown', { key: 'a', ctrlKey: true }),
    );
    expect(component.paletteOpen()).toBe(false);
  });

  // --- upload shortcut ---

  it('triggers a file pick on Shift+U', () => {
    component.onGlobalKeydown(
      new KeyboardEvent('keydown', { key: 'U', shiftKey: true }),
    );
    expect(uploadSvc.pick).toHaveBeenCalled();
  });

  it('does not hijack Shift+U while typing in a field', () => {
    const input = document.createElement('input');
    const event = new KeyboardEvent('keydown', { key: 'U', shiftKey: true });
    Object.defineProperty(event, 'target', { value: input });
    component.onGlobalKeydown(event);
    expect(uploadSvc.pick).not.toHaveBeenCalled();
  });

  // --- drop-anywhere ingest ---

  it('uploads files dropped onto the shell', () => {
    const file = new File(['x'], 'a.pdf');
    const event = new Event('drop') as DragEvent;
    Object.defineProperty(event, 'dataTransfer', {
      value: { files: [file], types: ['Files'] },
    });
    component.onDrop(event);
    expect(uploadSvc.upload).toHaveBeenCalled();
  });

  it('ignores a drop with no files', () => {
    const event = new Event('drop') as DragEvent;
    Object.defineProperty(event, 'dataTransfer', {
      value: { files: [], types: [] },
    });
    component.onDrop(event);
    expect(uploadSvc.upload).not.toHaveBeenCalled();
  });

  // --- init side effects ---

  it('loads the profile on init', () => {
    expect(authSvc.getProfile).toHaveBeenCalled();
  });

  it('loads the unread count on init', () => {
    expect(notifSvc.getUnreadCount).toHaveBeenCalled();
    expect(component.unreadCount()).toBe(3);
  });

  it('refreshes shell stats on init', () => {
    expect(statsSvc.refresh).toHaveBeenCalled();
  });

  it('cleans up the poll subscription on destroy', () => {
    expect(() => component.ngOnDestroy()).not.toThrow();
  });
});
