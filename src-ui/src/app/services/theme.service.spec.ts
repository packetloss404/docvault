import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { vi, describe, beforeEach, it, expect } from 'vitest';

import { ThemeService } from './theme.service';
import { PreferencesService } from './preferences.service';

function buildPreferences(prefs: Record<string, unknown> = {}) {
  return {
    getPreferences: vi.fn(() => of(prefs)),
    updatePreferences: vi.fn(() => of({})),
  };
}

function create(prefs: Record<string, unknown> = {}) {
  const preferences = buildPreferences(prefs);
  TestBed.configureTestingModule({
    providers: [
      ThemeService,
      { provide: PreferencesService, useValue: preferences },
    ],
  });
  return { service: TestBed.inject(ThemeService), preferences };
}

describe('ThemeService', () => {
  beforeEach(() => {
    TestBed.resetTestingModule();
    localStorage.clear();
    document.body.removeAttribute('data-theme');
    document.body.removeAttribute('data-accent');
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );
  });

  it('defaults to dark with the teal accent', () => {
    const { service } = create();
    expect(service.mode()).toBe('dark');
    expect(service.accent()).toBe('teal');
  });

  it('applies the theme to the body on construction', () => {
    create();
    expect(document.body.getAttribute('data-theme')).toBe('dark');
    expect(document.body.getAttribute('data-accent')).toBe('teal');
  });

  it('mirrors the theme onto data-bs-theme for the Bootstrap bridge', () => {
    create();
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
  });

  it('restores a persisted mode from localStorage', () => {
    localStorage.setItem('dv_theme', 'light');
    const { service } = create();
    expect(service.mode()).toBe('light');
    expect(document.body.getAttribute('data-theme')).toBe('light');
  });

  it('restores a persisted accent from localStorage', () => {
    localStorage.setItem('dv_accent', 'amber');
    const { service } = create();
    expect(service.accent()).toBe('amber');
  });

  it('ignores an unknown persisted accent', () => {
    localStorage.setItem('dv_accent', 'magenta');
    const { service } = create();
    expect(service.accent()).toBe('teal');
  });

  it('resolves system mode against the OS preference', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );
    localStorage.setItem('dv_theme', 'system');
    const { service } = create();
    expect(service.mode()).toBe('system');
    expect(service.resolved()).toBe('dark');
  });

  it('persists a mode change to the server and localStorage', () => {
    const { service, preferences } = create();
    service.setMode('light');
    expect(service.mode()).toBe('light');
    expect(localStorage.getItem('dv_theme')).toBe('light');
    expect(preferences.updatePreferences).toHaveBeenCalledWith({ theme: 'light' });
  });

  it('cycles dark to light to system and back', () => {
    const { service } = create();
    service.cycleMode();
    expect(service.mode()).toBe('light');
    service.cycleMode();
    expect(service.mode()).toBe('system');
    service.cycleMode();
    expect(service.mode()).toBe('dark');
  });

  it('persists an accent change', () => {
    const { service, preferences } = create();
    service.setAccent('periwinkle');
    expect(document.body.getAttribute('data-accent')).toBe('periwinkle');
    expect(preferences.updatePreferences).toHaveBeenCalledWith({
      accent: 'periwinkle',
    });
  });

  it('adopts server preferences on load', () => {
    const { service } = create({ theme: 'light', accent: 'chartreuse' });
    service.load();
    expect(service.mode()).toBe('light');
    expect(service.accent()).toBe('chartreuse');
  });

  it('ignores an unknown accent from the server', () => {
    const { service } = create({ accent: 'neon' });
    service.load();
    expect(service.accent()).toBe('teal');
  });

  it('still applies a theme when preferences fail to load', () => {
    const preferences = {
      getPreferences: vi.fn(() => throwError(() => new Error('offline'))),
      updatePreferences: vi.fn(() => of({})),
    };
    TestBed.configureTestingModule({
      providers: [
        ThemeService,
        { provide: PreferencesService, useValue: preferences },
      ],
    });
    const service = TestBed.inject(ThemeService);
    expect(() => service.load()).not.toThrow();
    expect(document.body.getAttribute('data-theme')).toBe('dark');
  });
});
