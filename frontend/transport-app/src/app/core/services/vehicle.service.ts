import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Vehicle {
  id: string;
  placa: string;
  marca: string;
  modelo: string;
  capacidad: number;
  transportistaId: string;
  conductorId?: string;
  estado: 'Disponible' | 'En Viaje' | 'Inactivo';
  transportistaNombre?: string;
  conductorNombre?: string;
}

export interface PaginatedVehicles {
  items: Vehicle[];
  total: number;
}

export type VehicleStatusFilter = 'todos' | 'Disponible' | 'En Viaje' | 'Inactivo';

@Injectable({
  providedIn: 'root'
})
export class VehicleService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getVehicles(
    page: number = 1,
    limit: number = 10,
    search: string = '',
    statusFilter: VehicleStatusFilter = 'todos'
  ): Observable<PaginatedVehicles> {
    const params: Record<string, string> = {
      page: String(page),
      limit: String(limit)
    };
    if (search.trim()) {
      params['search'] = search.trim();
    }
    if (statusFilter !== 'todos') {
      params['estado'] = statusFilter;
    }

    return this.http.get<PaginatedVehicles>(`${this.apiUrl}/vehicles`, { params }).pipe(
      catchError(() => of({ items: [], total: 0 }))
    );
  }

  getVehicleById(id: string): Observable<Vehicle | undefined> {
    return this.http.get<Vehicle>(`${this.apiUrl}/vehicles/${id}`).pipe(
      catchError(() => of(undefined))
    );
  }

  createVehicle(vehicle: Omit<Vehicle, 'id'>): Observable<Vehicle> {
    return this.http.post<Vehicle>(`${this.apiUrl}/vehicles`, vehicle).pipe(
      catchError(() => of({ id: '', ...vehicle }))
    );
  }

  updateVehicle(id: string, updates: Partial<Vehicle>): Observable<Vehicle> {
    return this.http.put<Vehicle>(`${this.apiUrl}/vehicles/${id}`, updates).pipe(
      catchError(() => of({
        id,
        placa: '',
        marca: '',
        modelo: '',
        capacidad: 0,
        transportistaId: '',
        estado: 'Disponible' as const,
        ...updates
      }))
    );
  }

  deleteVehicle(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/vehicles/${id}`).pipe(
      catchError(() => of(undefined as void))
    );
  }
}
