import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface AuditOperation {
  id: string;
  fechaHora: Date;
  tablaAfectada: string;
  idRegistroAfectado: string;
  accion: 'INSERT' | 'UPDATE' | 'DELETE';
  usuarioResponsable: string;
}

export interface AuditLogin {
  id: string;
  usuario: string;
  fechaHora: Date;
}

interface PaginatedResult<T> {
  items: T[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class AuditService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getOperations(
    page = 1,
    limit = 10,
    search = '',
    dateFrom?: Date,
    dateTo?: Date
  ): Observable<PaginatedResult<AuditOperation>> {
    const params: Record<string, string> = { page: String(page), limit: String(limit) };
    if (search.trim()) params['search'] = search.trim();
    if (dateFrom) params['dateFrom'] = dateFrom.toISOString();
    if (dateTo) params['dateTo'] = dateTo.toISOString();

    return this.http
      .get<PaginatedResult<AuditOperation>>(`${this.apiUrl}/audit/operations`, { params })
      .pipe(
        map(r => ({
          items: (r.items || []).map(op => ({ ...op, fechaHora: new Date(op.fechaHora) })),
          total: r.total || 0,
        })),
        catchError(() => of({ items: [], total: 0 }))
      );
  }

  getLogins(
    page = 1,
    limit = 10,
    search = '',
    dateFrom?: Date,
    dateTo?: Date
  ): Observable<PaginatedResult<AuditLogin>> {
    const params: Record<string, string> = { page: String(page), limit: String(limit) };
    if (search.trim()) params['search'] = search.trim();
    if (dateFrom) params['dateFrom'] = dateFrom.toISOString();
    if (dateTo) params['dateTo'] = dateTo.toISOString();

    return this.http
      .get<PaginatedResult<AuditLogin>>(`${this.apiUrl}/audit/logins`, { params })
      .pipe(
        map(r => ({
          items: (r.items || []).map(l => ({ ...l, fechaHora: new Date(l.fechaHora) })),
          total: r.total || 0,
        })),
        catchError(() => of({ items: [], total: 0 }))
      );
  }

  getRecentOperations(limit = 5): Observable<AuditOperation[]> {
    return this.getOperations(1, limit).pipe(map(r => r.items));
  }

  getRecentLogins(limit = 5): Observable<AuditLogin[]> {
    return this.getLogins(1, limit).pipe(map(r => r.items));
  }
}
