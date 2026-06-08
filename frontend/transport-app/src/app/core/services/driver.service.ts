import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Driver {
  id: string;
  fullName: string;
  cedula: string;
  telefono: string;
  correo: string;
  direccion: string;
  numeroLicencia: string;
  categoriaLicencia: 'C1' | 'C2' | 'C3' | 'C4';
  fechaVencimientoLicencia: string; // formato: YYYY-MM-DD
  transportistaId?: string;
}

export interface PaginatedDrivers {
  items: Driver[];
  total: number;
}

export type LicenseFilter = 'all' | 'expiring' | 'expired';

@Injectable({
  providedIn: 'root'
})
export class DriverService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Obtener estado de licencia: 'vigente', 'porVencer', 'vencida'
   */
  private getLicenseStatus(fechaVencimiento: string): 'vigente' | 'porVencer' | 'vencida' {
    const today = new Date();
    const expiryDate = new Date(fechaVencimiento);
    const daysUntilExpiry = Math.floor((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) {
      return 'vencida';
    } else if (daysUntilExpiry <= 90) {
      return 'porVencer';
    } else {
      return 'vigente';
    }
  }

  /**
   * Obtener conductores con filtro y búsqueda
   */
  getDrivers(page: number, limit: number, search: string = '', licenseFilter: LicenseFilter = 'all'): Observable<PaginatedDrivers> {
    const params: Record<string, string> = {
      page: String(page),
      limit: String(limit)
    };
    if (search.trim()) {
      params['search'] = search.trim();
    }
    if (licenseFilter !== 'all') {
      params['licenseFilter'] = licenseFilter;
    }

    return this.http.get<PaginatedDrivers>(`${this.apiUrl}/drivers`, { params }).pipe(
      catchError(() => of({ items: [], total: 0 }))
    );
  }

  /**
   * Obtener conductor por ID
   */
  getDriverById(id: string): Observable<Driver | undefined> {
    return this.http.get<Driver>(`${this.apiUrl}/drivers/${id}`).pipe(
      catchError(() => of(undefined))
    );
  }

  /**
   * Crear nuevo conductor
   */
  createDriver(driver: Omit<Driver, 'id'>): Observable<Driver> {
    return this.http.post<Driver>(`${this.apiUrl}/drivers`, driver).pipe(
      catchError(() => of({ id: '', ...driver }))
    );
  }

  /**
   * Actualizar conductor
   */
  updateDriver(id: string, updates: Partial<Driver>): Observable<Driver> {
    return this.http.put<Driver>(`${this.apiUrl}/drivers/${id}`, updates).pipe(
      catchError(() => of({
        id,
        fullName: '',
        cedula: '',
        telefono: '',
        correo: '',
        direccion: '',
        numeroLicencia: '',
        categoriaLicencia: 'C1' as const,
        fechaVencimientoLicencia: '',
        ...updates
      }))
    );
  }

  /**
   * Eliminar conductor
   */
  deleteDriver(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/drivers/${id}`).pipe(
      catchError(() => of(undefined as void))
    );
  }

  /**
   * Obtener conductores por estado de licencia (para contadores)
   * Llama a getDrivers sin paginación para obtener todos y calcula localmente.
   */
  getDriverCountByLicenseStatus(): Observable<{ vigentes: number; porVencer: number; vencidas: number }> {
    return this.http.get<PaginatedDrivers>(`${this.apiUrl}/drivers`, { params: { page: '1', limit: '1000' } }).pipe(
      map(result => {
        const drivers = result.items || [];
        const vigentes = drivers.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'vigente').length;
        const porVencer = drivers.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'porVencer').length;
        const vencidas = drivers.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'vencida').length;
        return { vigentes, porVencer, vencidas };
      }),
      catchError(() => of({ vigentes: 0, porVencer: 0, vencidas: 0 }))
    );
  }
}
