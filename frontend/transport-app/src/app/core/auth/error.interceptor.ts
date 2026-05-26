import { HttpInterceptorFn, HttpErrorResponse, HttpEvent } from '@angular/common/http';
import { throwError, Observable } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { inject } from '@angular/core';
import { Router } from '@angular/router';

export const errorInterceptor: HttpInterceptorFn = (req, next): Observable<HttpEvent<any>> => {
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'Error desconocido ocurrió';

      if (error.error instanceof ErrorEvent) {
        // Client-side error
        errorMessage = `Error: ${error.error.message}`;
      } else {
        // Server-side error
        switch (error.status) {
          case 400:
            errorMessage = error.error?.detail || 'Solicitud inválida. Verifique los datos enviados.';
            break;
          case 401:
            errorMessage = 'No autorizado. Inicie sesión nuevamente.';
            break;
          case 403:
            errorMessage = 'Acceso denegado. No tiene permisos para esta acción.';
            break;
          case 404:
            errorMessage = 'Recurso no encontrado.';
            break;
          case 409:
            errorMessage = error.error?.detail || 'Conflicto en los datos. Verifique que no exista duplicado.';
            break;
          case 422:
            // Validation error
            if (error.error?.detail) {
              if (Array.isArray(error.error.detail)) {
                errorMessage = error.error.detail
                  .map((err: any) => `${err.loc?.join('.')}: ${err.msg}`)
                  .join('; ');
              } else {
                errorMessage = error.error.detail;
              }
            } else {
              errorMessage = 'Errores de validación en los datos enviados.';
            }
            break;
          case 429:
            errorMessage = 'Demasiadas solicitudes. Por favor, intente más tarde.';
            break;
          case 500:
            errorMessage = 'Error en el servidor. Por favor, intente más tarde.';
            break;
          case 503:
            errorMessage = 'Servicio no disponible. Por favor, intente más tarde.';
            break;
          default:
            errorMessage = `Error ${error.status}: ${error.statusText}`;
        }
      }

      console.error('HTTP Error:', {
        status: error.status,
        message: errorMessage,
        error: error.error
      });

      // Pass error with message to caller
      return throwError(() => ({
        status: error.status,
        message: errorMessage,
        details: error.error
      }));
    })
  );
};
