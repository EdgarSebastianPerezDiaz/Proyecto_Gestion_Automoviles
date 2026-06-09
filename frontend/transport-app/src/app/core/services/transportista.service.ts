import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Transportista {
  id: string;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  correo: string;
  tipoDocumento?: 'NIT' | 'Cédula';
}

@Injectable({
  providedIn: 'root'
})
export class TransportistaService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getAll(): Observable<Transportista[]> {
    return this.http.get<{ items: Transportista[]; total: number }>(`${this.apiUrl}/clients`).pipe(
      map(r => r.items || []),
      catchError(() => of([]))
    );
  }

  getById(id: string): Observable<Transportista | undefined> {
    return this.http.get<Transportista>(`${this.apiUrl}/clients/${id}`).pipe(
      catchError(() => of(undefined))
    );
  }

  create(transportista: Omit<Transportista, 'id'>): Observable<Transportista> {
    return this.http.post<Transportista>(`${this.apiUrl}/clients`, transportista).pipe(
      catchError(() => of({ id: '', ...transportista }))
    );
  }

  update(id: string, updates: Partial<Transportista>): Observable<Transportista> {
    return this.http.put<Transportista>(`${this.apiUrl}/clients/${id}`, updates).pipe(
      catchError(() => of({ id, nombre: '', nit: '', direccion: '', telefono: '', correo: '', ...updates }))
    );
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/clients/${id}`).pipe(
      catchError(() => of(undefined as void))
    );
  }
}
