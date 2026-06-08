import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Company {
  id: string;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  correo: string;
}

export interface PaginatedCompanies {
  items: Company[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class CompanyService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Obtiene empresas con paginación y búsqueda
   */
  getCompanies(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedCompanies> {
    const params: Record<string, string> = {
      page: String(page),
      limit: String(limit)
    };
    if (search.trim()) {
      params['search'] = search.trim();
    }

    return this.http.get<PaginatedCompanies>(`${this.apiUrl}/companies`, { params }).pipe(
      catchError(() => of({ items: [], total: 0 }))
    );
  }

  /**
   * Obtiene una empresa por ID
   */
  getCompanyById(id: string): Observable<Company | undefined> {
    return this.http.get<Company>(`${this.apiUrl}/companies/${id}`).pipe(
      catchError(() => of(undefined))
    );
  }

  /**
   * Crea una nueva empresa
   */
  createCompany(company: Omit<Company, 'id'>): Observable<Company> {
    return this.http.post<Company>(`${this.apiUrl}/companies`, company).pipe(
      catchError(() => of({ id: '', ...company }))
    );
  }

  /**
   * Actualiza una empresa existente
   */
  updateCompany(id: string, updates: Partial<Company>): Observable<Company> {
    return this.http.put<Company>(`${this.apiUrl}/companies/${id}`, updates).pipe(
      catchError(() => of({ id, nombre: '', nit: '', direccion: '', telefono: '', correo: '', ...updates }))
    );
  }

  /**
   * Elimina una empresa
   */
  deleteCompany(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/companies/${id}`).pipe(
      catchError(() => of(undefined as void))
    );
  }
}
