import { HttpInterceptorFn, HttpErrorResponse, HttpEvent, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';
import { Router } from '@angular/router';
import { BehaviorSubject, throwError, Observable, EMPTY } from 'rxjs';
import { catchError, filter, take, concatMap } from 'rxjs/operators';

let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<string | null>(null);

export const authInterceptor: HttpInterceptorFn = (req, next): Observable<HttpEvent<any>> => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Skip adding token to auth endpoints
  const authEndpoints = ['/auth/login', '/auth/refresh', '/auth/register'];
  const isAuthEndpoint = authEndpoints.some(endpoint => req.url.includes(endpoint));

  if (!isAuthEndpoint) {
    const token = authService.getAccessToken();
    if (token) {
      req = addTokenToRequest(req, token);
    }
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !isAuthEndpoint) {
        return handle401Error(req, next, authService, router);
      }
      return throwError(() => error);
    })
  );
};

function addTokenToRequest(req: HttpRequest<any>, token: string): HttpRequest<any> {
  return req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });
}

function handle401Error(
  req: HttpRequest<any>,
  next: HttpHandlerFn,
  authService: AuthService,
  router: Router
): Observable<HttpEvent<any>> {
  // If the failed request is a login attempt, do not attempt refresh to avoid loops
  if (req.url.includes('/auth/login')) {
    return throwError(() => new Error('Unauthorized on login'));
  }
  if (!isRefreshing) {
    isRefreshing = true;
    refreshTokenSubject.next(null);

    return authService.refreshToken().pipe(
      concatMap((response: any) => {
        isRefreshing = false;
        const token = response.access_token;
        refreshTokenSubject.next(token);
        return next(addTokenToRequest(req, token));
      }),
      catchError((error) => {
        isRefreshing = false;
        authService.logout().subscribe();
        router.navigate(['/login']);
        return throwError(() => error);
      })
    );
  } else {
    // Wait for token and retry request
    return refreshTokenSubject.pipe(
      filter((token): token is string => token !== null),
      take(1),
      concatMap((token) => next(addTokenToRequest(req, token)))
    );
  }
}
