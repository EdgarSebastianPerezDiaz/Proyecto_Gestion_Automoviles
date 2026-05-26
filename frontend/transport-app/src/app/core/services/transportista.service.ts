import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

export interface Transportista {
  id: string;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  correo: string;
  tipoDocumento?: 'NIT' | 'Cédula';
}

const MOCK_TRANSPORTISTAS: Transportista[] = [
  { id: 'T1', nombre: 'Jaime Galindo Transportes', nit: '12.345.678-9', direccion: 'Calle 10 #5-67, Sogamoso', telefono: '310 555 0001', correo: 'jaime@galindo.com', tipoDocumento: 'Cédula' },
  { id: 'T2', nombre: 'Avance MC S.A.S.', nit: '98.765.432-1', direccion: 'Cra 20 #15-30, Duitama', telefono: '315 555 0004', correo: 'contacto@avancemc.com', tipoDocumento: 'NIT' }
];

@Injectable({
  providedIn: 'root'
})
export class TransportistaService {
  private transportistas: Transportista[] = [...MOCK_TRANSPORTISTAS];
  private nextId = 3;

  getAll(): Observable<Transportista[]> {
    return of(this.transportistas.map(transportista => ({ ...transportista }))).pipe(delay(300));
  }

  getById(id: string): Observable<Transportista | undefined> {
    return of(this.transportistas.find(transportista => transportista.id === id)).pipe(
      delay(300),
      map(transportista => transportista ? { ...transportista } : undefined)
    );
  }

  create(transportista: Omit<Transportista, 'id'>): Observable<Transportista> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const created: Transportista = {
          ...transportista,
          id: `T${this.nextId}`
        };
        this.nextId++;
        this.transportistas.push(created);
        return { ...created };
      })
    );
  }

  update(id: string, updates: Partial<Transportista>): Observable<Transportista> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.transportistas.findIndex(transportista => transportista.id === id);
        if (index === -1) {
          throw new Error(`Transportista with id ${id} not found`);
        }

        this.transportistas[index] = { ...this.transportistas[index], ...updates, id };
        return { ...this.transportistas[index] };
      })
    );
  }

  delete(id: string): Observable<void> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.transportistas.findIndex(transportista => transportista.id === id);
        if (index > -1) {
          this.transportistas.splice(index, 1);
        }
      })
    );
  }
}
