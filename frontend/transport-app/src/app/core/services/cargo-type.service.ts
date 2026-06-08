import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

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

const MOCK_CARGO_TYPES: CargoType[] = [
  {
    id: 'CAR-001',
    nombre: 'Acero estructural',
    descripcion: 'Vigas y perfiles laminados en caliente',
    pesoReferencia: 28.5,
    precioPorTon: 320000
  },
  {
    id: 'CAR-002',
    nombre: 'Chatarra metálica',
    descripcion: 'Retales y residuos de acero para reciclaje',
    pesoReferencia: 32,
    precioPorTon: 180000
  },
  {
    id: 'CAR-003',
    nombre: 'Tubería industrial',
    descripcion: 'Tubería de acero para construcción civil',
    pesoReferencia: 25,
    precioPorTon: 290000
  }
];

@Injectable({
  providedIn: 'root'
})
export class CargoTypeService {
  private cargoTypes: CargoType[] = [...MOCK_CARGO_TYPES];
  private nextId = 4;

  getCargoTypes(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedCargoTypes> {
    return of(null).pipe(
      delay(300),
      map(() => {
        let filtered = [...this.cargoTypes];

        if (search.trim()) {
          const searchTerm = search.toLowerCase().trim();
          filtered = filtered.filter(cargoType =>
            cargoType.nombre.toLowerCase().includes(searchTerm) ||
            cargoType.descripcion.toLowerCase().includes(searchTerm)
          );
        }

        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit).map(cargoType => ({ ...cargoType }));

        return { items, total };
      })
    );
  }

  getCargoTypeById(id: string): Observable<CargoType | undefined> {
    return of(this.cargoTypes.find(cargoType => cargoType.id === id)).pipe(
      delay(300),
      map(cargoType => cargoType ? { ...cargoType } : undefined)
    );
  }

  createCargoType(cargoType: Omit<CargoType, 'id'>): Observable<CargoType> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const created: CargoType = {
          ...cargoType,
          id: `CAR-${String(this.nextId).padStart(3, '0')}`
        };
        this.nextId++;
        this.cargoTypes.push(created);
        return { ...created };
      })
    );
  }

  updateCargoType(id: string, updates: Partial<CargoType>): Observable<CargoType> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.cargoTypes.findIndex(cargoType => cargoType.id === id);
        if (index === -1) {
          throw new Error(`CargoType with id ${id} not found`);
        }

        this.cargoTypes[index] = { ...this.cargoTypes[index], ...updates, id };
        return { ...this.cargoTypes[index] };
      })
    );
  }

  deleteCargoType(id: string): Observable<void> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.cargoTypes.findIndex(cargoType => cargoType.id === id);
        if (index > -1) {
          this.cargoTypes.splice(index, 1);
        }
      })
    );
  }
}
