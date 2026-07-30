import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterModule],
  styleUrl: './forbidden.component.scss',
  template: `
    <div class="dv-screen fb-screen">
      <div class="fb-card">
        <div class="fb-code">403</div>
        <h1 class="dv-h1 dv-h1--sm">Access denied</h1>
        <p class="fb-prose">
          You do not have permission to open this screen. Administration is restricted to staff
          accounts.
        </p>
        <div class="fb-actions">
          <a class="dv-btn dv-btn--primary" routerLink="/">← Back to dashboard</a>
        </div>
      </div>
    </div>
  `,
})
export class ForbiddenComponent {}
