import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) {
    return router.createUrlTree(['/login']);
  }

  const user = auth.currentUser();
  if (user?.is_staff || user?.is_superuser) {
    return true;
  }
  if (!user) {
    return auth.getProfile().pipe(
      map((profile) =>
        profile.is_staff || profile.is_superuser
          ? true
          : router.createUrlTree(['/403']),
      ),
      catchError(() => of(router.createUrlTree(['/login']))),
    );
  }

  return router.createUrlTree(['/403']);
};
