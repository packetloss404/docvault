import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export type DvIconName =
  | 'grid'
  | 'doc'
  | 'search'
  | 'tag'
  | 'pen'
  | 'flow'
  | 'inbox'
  | 'link'
  | 'shield'
  | 'gear'
  | 'theme'
  | 'bell'
  | 'folder';

/**
 * The Console icon set: geometric line icons on an 18x18 grid, 1.5px stroke,
 * drawn in `currentColor` so the rail/hover states colour them via CSS.
 *
 * Deliberately not Bootstrap Icons — the thin geometric style is part of the
 * design, and BI's filled/rounded shapes read as a different system.
 */
@Component({
  selector: 'dv-icon',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      aria-hidden="true"
      focusable="false"
      style="display:block"
    >
      @switch (name()) {
        @case ('grid') {
          <rect x="3" y="3" width="5" height="5" />
          <rect x="10" y="3" width="5" height="5" />
          <rect x="3" y="10" width="5" height="5" />
          <rect x="10" y="10" width="5" height="5" />
        }
        @case ('doc') {
          <rect x="3" y="2" width="12" height="14" rx="1" />
          <line x1="6" y1="6" x2="12" y2="6" />
          <line x1="6" y1="9" x2="12" y2="9" />
          <line x1="6" y1="12" x2="10" y2="12" />
        }
        @case ('search') {
          <circle cx="8" cy="8" r="5" />
          <line x1="12" y1="12" x2="16" y2="16" />
        }
        @case ('tag') {
          <path d="M2 2 L8 2 L16 10 L10 16 L2 8 Z" />
          <circle cx="6" cy="6" r="1.3" fill="currentColor" stroke="none" />
        }
        @case ('pen') {
          <path d="M3 15 L4 11 L12 3 L15 6 L7 14 Z" />
          <line x1="3" y1="15" x2="6" y2="14" />
        }
        @case ('flow') {
          <rect x="2" y="2" width="5" height="5" rx="1" />
          <rect x="11" y="11" width="5" height="5" rx="1" />
          <path d="M7 4.5 L13.5 4.5 L13.5 11" />
        }
        @case ('inbox') {
          <path d="M2 10 L5 4 L13 4 L16 10 L16 14 L2 14 Z" />
          <path d="M2 10 L6.5 10 L7.5 12 L10.5 12 L11.5 10 L16 10" />
        }
        @case ('link') {
          <circle cx="5" cy="9" r="3" />
          <circle cx="13" cy="9" r="3" />
          <line x1="7" y1="9" x2="11" y2="9" />
        }
        @case ('shield') {
          <path d="M9 2 L15 4.5 L15 9.5 C15 13.5 9 16 9 16 C9 16 3 13.5 3 9.5 L3 4.5 Z" />
        }
        @case ('gear') {
          <circle cx="9" cy="9" r="5.5" />
          <circle cx="9" cy="9" r="2" fill="currentColor" stroke="none" />
        }
        @case ('theme') {
          <circle cx="9" cy="9" r="6" />
          <path d="M9 3 A6 6 0 0 1 9 15 Z" fill="currentColor" stroke="none" />
        }
        @case ('bell') {
          <path d="M9 3 C6 3 5 5 5 8 L5 11 L3.5 13 L14.5 13 L13 11 L13 8 C13 5 12 3 9 3 Z" />
          <path d="M7.5 15 A1.5 1.5 0 0 0 10.5 15" />
        }
        @case ('folder') {
          <path d="M2 5 L2 14 L16 14 L16 6 L9 6 L7.5 4 L2 4 Z" />
        }
      }
    </svg>
  `,
})
export class IconComponent {
  readonly name = input.required<DvIconName>();
  readonly size = input(17);
}
