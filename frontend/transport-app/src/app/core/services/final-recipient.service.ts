import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface FinalRecipient {
  id: string;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  correo: string;
}

@Injectable({
  providedIn: 'root'
})
export class FinalRecipientService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getAll(): Observable<FinalRecipient[]> {
    return this.http.get<FinalRecipient[]>(`${this.apiUrl}/final-recipients`).pipe(
      catchError(() => of([]))
    );
  }

  getById(id: string): Observable<FinalRecipient | undefined> {
    return this.http.get<FinalRecipient>(`${this.apiUrl}/final-recipients/${id}`).pipe(
      catchError(() => of(undefined))
    );
  }

  create(finalRecipient: Omit<FinalRecipient, 'id'>): Observable<FinalRecipient> {
    return this.http.post<FinalRecipient>(`${this.apiUrl}/final-recipients`, finalRecipient).pipe(
      catchError(() => of({ id: '', ...finalRecipient }))
    );
  }

  update(id: string, updates: Partial<FinalRecipient>): Observable<FinalRecipient> {
    return this.http.put<FinalRecipient>(`${this.apiUrl}/final-recipients/${id}`, updates).pipe(
      catchError(() => of({ id, nombre: '', nit: '', direccion: '', telefono: '', correo: '', ...updates }))
    );
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/final-recipients/${id}`).pipe(
      catchError(() => of(undefined as void))
    );
  }
}
