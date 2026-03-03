import { inject } from '@angular/core';
import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  const auth = inject(AuthService);
  const token = auth.token();

  if (token) {
    const cloned = req.clone({
      setHeaders: { Authorization: `Token ${token}` },
    });
    return next(cloned);
  }

  return next(req);
};
