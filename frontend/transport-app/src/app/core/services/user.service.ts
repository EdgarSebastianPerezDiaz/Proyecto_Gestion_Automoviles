import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface User {
  id: string;
  nombre: string;
  email?: string;
  rol: 'administrador' | 'operario';
  ultimoAcceso?: Date;
  isActive: boolean;
  createdAt: Date;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getUsers(
    page = 1,
    limit = 10,
    search = '',
    rolFilter: 'administrador' | 'operario' | 'todos' = 'todos'
  ): Observable<{ items: User[]; total: number }> {
    const params: Record<string, string> = { page: String(page), limit: String(limit) };
    if (search.trim()) params['search'] = search.trim();
    if (rolFilter !== 'todos') params['rol'] = rolFilter;

    return this.http
      .get<{ items: User[]; total: number }>(`${this.apiUrl}/users`, { params })
      .pipe(
        map(r => ({
          items: (r.items || []).map(u => ({
            ...u,
            ultimoAcceso: u.ultimoAcceso ? new Date(u.ultimoAcceso) : undefined,
            createdAt: new Date(u.createdAt),
          })),
          total: r.total || 0,
        })),
        catchError(() => of({ items: [], total: 0 }))
      );
  }

  getUserById(id: string): Observable<User | undefined> {
    return this.http.get<User>(`${this.apiUrl}/users/${id}`).pipe(
      map(u => ({ ...u, createdAt: new Date(u.createdAt) })),
      catchError(() => of(undefined))
    );
  }

  createUser(
    payload: Omit<User, 'id' | 'createdAt' | 'isActive'> & { password: string }
  ): Observable<User> {
    return this.http
      .post<User>(`${this.apiUrl}/auth/register`, {
        email: payload.email,
        password: payload.password,
        full_name: payload.nombre,
        role: payload.rol === 'administrador' ? 'admin' : 'operator',
      })
      .pipe(
        map(u => ({
          ...u,
          nombre: u.nombre ?? payload.nombre,
          createdAt: new Date(),
          isActive: true,
        })),
        catchError(() =>
          of({
            id: '',
            nombre: payload.nombre,
            email: payload.email,
            rol: payload.rol,
            isActive: true,
            createdAt: new Date(),
          })
        )
      );
  }

  updateUser(id: string, updates: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/users/${id}`, updates).pipe(
      map(u => ({ ...u, createdAt: new Date(u.createdAt) })),
      catchError(() =>
        of({
          id,
          nombre: updates.nombre ?? '',
          email: updates.email,
          rol: updates.rol ?? 'operario',
          isActive: updates.isActive ?? true,
          createdAt: new Date(),
        })
      )
    );
  }

  deleteUser(id: string): Observable<boolean> {
    return this.http
      .delete<void>(`${this.apiUrl}/users/${id}`)
      .pipe(
        map(() => true),
        catchError(() => of(false))
      );
  }

  getAdminPrincipal(): Observable<User | undefined> {
    return this.getUsers(1, 1, '', 'administrador').pipe(
      map(r => r.items[0]),
      catchError(() => of(undefined))
    );
  }
}
