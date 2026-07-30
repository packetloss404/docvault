import { Injectable, computed, inject, signal } from '@angular/core';
import { PreferencesService } from './preferences.service';

export type ThemeMode = 'light' | 'dark' | 'system';
export type AccentName = 'teal' | 'chartreuse' | 'amber' | 'periwinkle';

export const ACCENTS: readonly AccentName[] = [
  'teal',
  'chartreuse',
  'amber',
  'periwinkle',
];

const THEME_KEY = 'dv_theme';
const ACCENT_KEY = 'dv_accent';

/**
 * Owns the `data-theme` / `data-accent` attributes the token layer keys off.
 *
 * Both are cached in localStorage and applied synchronously at construction so
 * the first paint is already correct; the server preference is loaded after
 * login and wins if it differs.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly preferences = inject(PreferencesService);

  private readonly modeSignal = signal<ThemeMode>(this.readMode());
  private readonly accentSignal = signal<AccentName>(this.readAccent());
  private readonly systemDark = signal(this.prefersDark());

  readonly mode = this.modeSignal.asReadonly();
  readonly accent = this.accentSignal.asReadonly();

  /** The theme actually rendered — `system` resolved against the OS setting. */
  readonly resolved = computed<'light' | 'dark'>(() => {
    const mode = this.modeSignal();
    if (mode === 'system') return this.systemDark() ? 'dark' : 'light';
    return mode;
  });

  constructor() {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    query.addEventListener('change', (e) => {
      this.systemDark.set(e.matches);
      this.apply();
    });
    this.apply();
  }

  /** Pull the persisted preference once the user is known. */
  load(): void {
    this.preferences.getPreferences().subscribe({
      next: (prefs) => {
        const theme = prefs.theme;
        if (theme === 'light' || theme === 'dark' || theme === 'system') {
          this.modeSignal.set(theme);
          localStorage.setItem(THEME_KEY, theme);
        }
        const accent = prefs['accent'];
        if (typeof accent === 'string' && this.isAccent(accent)) {
          this.accentSignal.set(accent);
          localStorage.setItem(ACCENT_KEY, accent);
        }
        this.apply();
      },
      // Preferences are a nicety; a failed fetch must not block the shell.
      error: () => this.apply(),
    });
  }

  setMode(mode: ThemeMode): void {
    this.modeSignal.set(mode);
    localStorage.setItem(THEME_KEY, mode);
    this.apply();
    this.preferences.updatePreferences({ theme: mode }).subscribe({
      error: () => {},
    });
  }

  /** Cycles dark → light → system, matching the single rail toggle. */
  cycleMode(): void {
    const next: Record<ThemeMode, ThemeMode> = {
      dark: 'light',
      light: 'system',
      system: 'dark',
    };
    this.setMode(next[this.modeSignal()]);
  }

  setAccent(accent: AccentName): void {
    this.accentSignal.set(accent);
    localStorage.setItem(ACCENT_KEY, accent);
    this.apply();
    this.preferences.updatePreferences({ accent }).subscribe({
      error: () => {},
    });
  }

  private apply(): void {
    const theme = this.resolved();
    document.body.setAttribute('data-theme', theme);
    document.body.setAttribute('data-accent', this.accentSignal());
    // Keep Bootstrap's own switch in sync while components still use its classes.
    document.documentElement.setAttribute('data-bs-theme', theme);
  }

  private readMode(): ThemeMode {
    const stored = localStorage.getItem(THEME_KEY);
    return stored === 'light' || stored === 'dark' || stored === 'system'
      ? stored
      : 'dark';
  }

  private readAccent(): AccentName {
    const stored = localStorage.getItem(ACCENT_KEY);
    return stored && this.isAccent(stored) ? stored : 'teal';
  }

  private isAccent(value: string): value is AccentName {
    return (ACCENTS as readonly string[]).includes(value);
  }

  private prefersDark(): boolean {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
}
