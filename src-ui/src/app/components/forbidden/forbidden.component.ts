import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterModule],
  template: `
    <div class="d-flex flex-column align-items-center justify-content-center" style="min-height: 60vh;">
      <div class="text-center">
        <h1 class="display-1 fw-bold text-danger">403</h1>
        <h2 class="mb-3">Access Denied</h2>
        <p class="text-muted mb-4">
          You do not have permission to access this page.<br />
          This area is restricted to administrators only.
        </p>
        <a routerLink="/" class="btn btn-primary">
          <i class="bi bi-house me-2"></i>Back to Dashboard
        </a>
      </div>
    </div>
  `,
})
export class ForbiddenComponent {}
