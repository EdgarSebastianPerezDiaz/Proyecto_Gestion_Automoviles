import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface CargoType {
  id: string;
  nombre: string;
  descripcion: string;
  pesoReferencia?: number;
  precioPorTon: number;
}

export interface PaginatedCargoTypes {
  items: CargoType[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class CargoTypeService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getCargoTypes(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedCargoTypes> {
    const params: Record<string, string> = {
      page: String(page),
      limit: String(limit)
    };
    if (search.trim()) {
      params['search'] = search.trim();
    }

    return this.http.get<PaginatedCargoTypes>(`${this.apiUrl}/cargo-types`, { params }).pipe(
      catchError(() => of({ items: [], total: 0 }))
    );
  }

  getCargoTypeById(id: string): Observable<CargoType | undefined> {
    return this.http.get<CargoType>(`${this.apiUrl}/cargo-types/${id}`).pipe(
      catchError(() => of(undefined))
    );
  }

  createCargoType(cargoType: Omit<CargoType, 'id'>): Observable<CargoType> {
    return this.http.post<CargoType>(`${this.apiUrl}/cargo-types`, cargoType).pipe(
      catchError(() => of({ id: '', ...cargoType }))
    );
  }

  updateCargoType(id: string, updates: Partial<CargoType>): Observable<CargoType> {
    return this.http.put<CargoType>(`${this.apiUrl}/cargo-types/${id}`, updates).pipe(
      catchError(() => of({ id, nombre: '', descripcion: '', precioPorTon: 0, ...updates }))
    );
  }

  deleteCargoType(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/cargo-types/${id}`).pipe(
      catchError(() => of(undefined as void))
    );
  }
}
