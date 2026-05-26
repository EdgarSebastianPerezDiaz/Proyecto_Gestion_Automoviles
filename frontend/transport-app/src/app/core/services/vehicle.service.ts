import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

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

const TRANSPORTISTA_NAMES: Record<string, string> = {
  T1: 'Jaime Galindo Transportes',
  T2: 'Avance MC S.A.S.'
};

const DRIVER_NAMES: Record<string, string> = {
  '1': 'Jaime Galindo',
  '2': 'Sebastián Torres',
  '3': 'Carlos Mendoza'
};

const MOCK_VEHICLES: Vehicle[] = [
  {
    id: 'VEH-001',
    placa: 'XYZ-123',
    marca: 'Kenworth',
    modelo: 'T800',
    capacidad: 32,
    transportistaId: 'T1',
    conductorId: '1',
    estado: 'Disponible',
    transportistaNombre: TRANSPORTISTA_NAMES['T1'],
    conductorNombre: DRIVER_NAMES['1']
  },
  {
    id: 'VEH-002',
    placa: 'ABC-456',
    marca: 'Freightliner',
    modelo: 'Cascadia',
    capacidad: 28.5,
    transportistaId: 'T1',
    conductorId: '2',
    estado: 'En Viaje',
    transportistaNombre: TRANSPORTISTA_NAMES['T1'],
    conductorNombre: DRIVER_NAMES['2']
  },
  {
    id: 'VEH-003',
    placa: 'DEF-789',
    marca: 'International',
    modelo: 'LT625',
    capacidad: 30,
    transportistaId: 'T2',
    conductorId: '3',
    estado: 'Inactivo',
    transportistaNombre: TRANSPORTISTA_NAMES['T2'],
    conductorNombre: DRIVER_NAMES['3']
  }
];

@Injectable({
  providedIn: 'root'
})
export class VehicleService {
  private vehicles: Vehicle[] = [...MOCK_VEHICLES];
  private nextId = 4;

  constructor() {}

  private resolveTransportistaName(transportistaId: string): string {
    return TRANSPORTISTA_NAMES[transportistaId] || 'Sin transportista';
  }

  private resolveDriverName(conductorId?: string): string {
    if (!conductorId) {
      return 'Sin conductor';
    }

    return DRIVER_NAMES[conductorId] || 'Sin conductor';
  }

  private enrichVehicle(vehicle: Vehicle): Vehicle {
    return {
      ...vehicle,
      transportistaNombre: this.resolveTransportistaName(vehicle.transportistaId),
      conductorNombre: this.resolveDriverName(vehicle.conductorId)
    };
  }

  getVehicles(
    page: number = 1,
    limit: number = 10,
    search: string = '',
    statusFilter: VehicleStatusFilter = 'todos'
  ): Observable<PaginatedVehicles> {
    return of(null).pipe(
      delay(300),
      map(() => {
        let filtered = [...this.vehicles];

        if (statusFilter !== 'todos') {
          filtered = filtered.filter(vehicle => vehicle.estado === statusFilter);
        }

        if (search.trim()) {
          const searchTerm = search.toLowerCase().trim();
          filtered = filtered.filter(vehicle =>
            vehicle.placa.toLowerCase().includes(searchTerm) ||
            vehicle.marca.toLowerCase().includes(searchTerm) ||
            this.resolveDriverName(vehicle.conductorId).toLowerCase().includes(searchTerm)
          );
        }

        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit).map(vehicle => this.enrichVehicle(vehicle));

        return { items, total };
      })
    );
  }

  getVehicleById(id: string): Observable<Vehicle | undefined> {
    return of(this.vehicles.find(vehicle => vehicle.id === id)).pipe(
      delay(300),
      map(vehicle => vehicle ? this.enrichVehicle(vehicle) : undefined)
    );
  }

  createVehicle(vehicle: Omit<Vehicle, 'id'>): Observable<Vehicle> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const newVehicle: Vehicle = this.enrichVehicle({
          ...vehicle,
          id: `VEH-${String(this.nextId).padStart(3, '0')}`
        });
        this.nextId++;
        this.vehicles.push(newVehicle);
        return newVehicle;
      })
    );
  }

  updateVehicle(id: string, updates: Partial<Vehicle>): Observable<Vehicle> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.vehicles.findIndex(vehicle => vehicle.id === id);
        if (index === -1) {
          throw new Error(`Vehicle with id ${id} not found`);
        }

        const currentVehicle = this.vehicles[index];
        const updatedVehicle = this.enrichVehicle({
          ...currentVehicle,
          ...updates,
          id: currentVehicle.id
        });

        this.vehicles[index] = updatedVehicle;
        return updatedVehicle;
      })
    );
  }

  deleteVehicle(id: string): Observable<void> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.vehicles.findIndex(vehicle => vehicle.id === id);
        if (index > -1) {
          this.vehicles.splice(index, 1);
        }
      })
    );
  }
}
