import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

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

  private drivers: Driver[] = [
    {
      id: '1',
      fullName: 'Jaime Galindo',
      cedula: '12.345.678',
      telefono: '310 555 0001',
      correo: 'j.galindo@mail.com',
      direccion: 'Cra 10 #20-50, Bogotá',
      numeroLicencia: 'LIC-001234',
      categoriaLicencia: 'C3',
      fechaVencimientoLicencia: '2026-12-15',
      transportistaId: 'T1'
    },
    {
      id: '2',
      fullName: 'Sebastián Torres',
      cedula: '98.765.432',
      telefono: '315 555 0002',
      correo: 's.torres@mail.com',
      direccion: 'Cra 5 #12-34, Tunja',
      numeroLicencia: 'LIC-005678',
      categoriaLicencia: 'C2',
      fechaVencimientoLicencia: '2026-03-23',
      transportistaId: 'T1'
    },
    {
      id: '3',
      fullName: 'Carlos Mendoza',
      cedula: '55.111.222',
      telefono: '320 555 0003',
      correo: 'c.mendoza@mail.com',
      direccion: 'Av. Colón #8-20, Sogamoso',
      numeroLicencia: 'LIC-009900',
      categoriaLicencia: 'C4',
      fechaVencimientoLicencia: '2026-01-01',
      transportistaId: 'T2'
    }
  ];

  constructor() { }

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
    let filtered = [...this.drivers];

    // Filtrar por estado de licencia
    if (licenseFilter === 'expiring') {
      filtered = filtered.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'porVencer');
    } else if (licenseFilter === 'expired') {
      filtered = filtered.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'vencida');
    }

    // Filtrar por búsqueda
    if (search.trim()) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(d =>
        d.fullName.toLowerCase().includes(searchLower) ||
        d.cedula.includes(search) ||
        d.numeroLicencia.toLowerCase().includes(searchLower)
      );
    }

    // Paginación
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const items = filtered.slice(startIndex, endIndex);

    return of({
      items,
      total: filtered.length
    }).pipe(delay(500));
  }

  /**
   * Obtener conductor por ID
   */
  getDriverById(id: string): Observable<Driver | undefined> {
    return of(this.drivers.find(d => d.id === id)).pipe(delay(300));
  }

  /**
   * Crear nuevo conductor
   */
  createDriver(driver: Omit<Driver, 'id'>): Observable<Driver> {
    const newId = (Math.max(...this.drivers.map(d => parseInt(d.id)), 0) + 1).toString();
    const newDriver: Driver = { ...driver, id: newId };
    this.drivers.push(newDriver);
    return of(newDriver).pipe(delay(500));
  }

  /**
   * Actualizar conductor
   */
  updateDriver(id: string, updates: Partial<Driver>): Observable<Driver> {
    const driver = this.drivers.find(d => d.id === id);
    if (driver) {
      Object.assign(driver, updates);
    }
    return of(driver!).pipe(delay(500));
  }

  /**
   * Eliminar conductor
   */
  deleteDriver(id: string): Observable<void> {
    const index = this.drivers.findIndex(d => d.id === id);
    if (index > -1) {
      this.drivers.splice(index, 1);
    }
    return of(void 0).pipe(delay(500));
  }

  /**
   * Obtener conductores por estado de licencia (para contadores)
   */
  getDriverCountByLicenseStatus(): Observable<{ vigentes: number; porVencer: number; vencidas: number }> {
    const vigentes = this.drivers.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'vigente').length;
    const porVencer = this.drivers.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'porVencer').length;
    const vencidas = this.drivers.filter(d => this.getLicenseStatus(d.fechaVencimientoLicencia) === 'vencida').length;

    return of({ vigentes, porVencer, vencidas }).pipe(delay(300));
  }
}
