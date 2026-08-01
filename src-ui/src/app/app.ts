import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ThemeService } from './services/theme.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
export class App {
  // Injected at the root so the theme and accent apply on every route, not only
  // inside the authenticated shell. Previously ThemeService was first
  // constructed by LayoutComponent, so /login and the public pages always
  // rendered dark regardless of the stored preference.
  private readonly theme = inject(ThemeService);
}
