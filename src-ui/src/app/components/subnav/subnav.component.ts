import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Event as RouterEvent } from '@angular/router';
import { filter, map, startWith } from 'rxjs';
import { RAIL, SubNavItem, isUnder, railItemFor } from '../../nav';

/**
 * Peer-screen switcher for a rail cluster.
 *
 * It derives both the item list and the active item from the current URL, so a
 * screen only has to drop `<dv-subnav />` at the top of its template — there is
 * no per-screen list to keep in sync with `nav.ts`.
 */
@Component({
  selector: 'dv-subnav',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (items().length) {
      @if (variant() === 'tab') {
        <div class="dv-tabs">
          @for (item of items(); track item.path) {
            <a
              class="dv-tab"
              [class.is-active]="isActive(item)"
              [routerLink]="item.path"
              >{{ item.label }}</a
            >
          }
          <ng-content select="[subnavAction]" />
        </div>
      } @else {
        <div class="dv-navchips">
          @for (item of items(); track item.path) {
            <a
              class="dv-navchip"
              [class.is-active]="isActive(item)"
              [routerLink]="item.path"
              >{{ item.label }}</a
            >
          }
        </div>
      }
    }
  `,
})
export class SubnavComponent {
  private readonly router = inject(Router);

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((e: RouterEvent): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  private readonly cluster = computed(() => railItemFor(this.url()));

  readonly items = computed<readonly SubNavItem[]>(
    () => this.cluster()?.sub ?? [],
  );

  readonly variant = computed(() => this.cluster()?.subVariant ?? 'chip');

  isActive(item: SubNavItem): boolean {
    return isUnder(this.url(), item.path);
  }
}

/** Re-exported so callers can assert the rail covers a route. */
export { RAIL };
