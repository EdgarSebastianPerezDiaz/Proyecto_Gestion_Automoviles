import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Driver {
  id: string;
  name: string;
  license: string;
}

export interface Vehicle {
  id: string;
  plate: string;
  type: string;
}

export type TripStatus = 'Programado' | 'En Ruta' | 'Entregado' | 'Cancelado';
export type LegacyTripStatus = 'Programado' | 'En Ruta' | 'Completado' | 'Cancelado';

export interface TripDocuments {
  ordenCargueUrl?: string;
  manifiestoUrl?: string;
  cumplidoUrl?: string;
}

export interface LegacyTripDocuments {
  waybillNumber: string;
  invoiceNumbers: string[];
  status: string;
}

export interface Trip {
  id: string;
  origenId: string;
  destinoId: string;
  transportistaId: string;
  conductorId: string;
  vehiculoId: string;
  cargoTypeId: string;
  peso: number;
  costoTotal: number;
  fechaSalida: Date;
  fechaLlegadaEstimada: Date;
  fechaLlegadaReal?: Date;
  estado: TripStatus;
  documentos: TripDocuments;
  precioPorTon?: number;
  origenNombre?: string;
  destinoNombre?: string;
  transportistaNombre?: string;
  conductorNombre?: string;
  vehiculoPlaca?: string;
  cargoTypeNombre?: string;
  vehiculoCapacidad?: number;
  origin: string;
  destination: string;
  driver: Driver;
  vehicle: Vehicle;
  status: LegacyTripStatus;
  startDate: Date;
  estimatedEndDate: Date;
  actualEndDate?: Date;
  cargoWeight: number;
  cargoType: string;
  documents: LegacyTripDocuments;
}

export interface PaginatedTrips {
  items: Trip[];
  total: number;
}

export interface TripReportRow {
  id: string;
  origin: string;
  destination: string;
  conductor: string;
  fechaSalida: Date;
  costoTotal: number;
  estado: TripStatus;
}

/** Normalize dates in a trip object returned from the API (strings → Date). */
function hydrateTrip(raw: any): Trip {
  const estado: TripStatus = raw.estado ?? 'Programado';
  const normalizedStatus: LegacyTripStatus = estado === 'Entregado' ? 'Completado' : estado;

  const fechaSalida = raw.fechaSalida ? new Date(raw.fechaSalida) : new Date();
  const fechaLlegadaEstimada = raw.fechaLlegadaEstimada ? new Date(raw.fechaLlegadaEstimada) : new Date();
  const fechaLlegadaReal = raw.fechaLlegadaReal ? new Date(raw.fechaLlegadaReal) : undefined;

  return {
    ...raw,
    estado,
    fechaSalida,
    fechaLlegadaEstimada,
    fechaLlegadaReal,
    documentos: raw.documentos ?? {},
    origin: raw.origin ?? raw.origenNombre ?? '',
    destination: raw.destination ?? raw.destinoNombre ?? '',
    driver: raw.driver ?? { id: raw.conductorId ?? '', name: raw.conductorNombre ?? '', license: '' },
    vehicle: raw.vehicle ?? { id: raw.vehiculoId ?? '', plate: raw.vehiculoPlaca ?? '', type: '' },
    status: raw.status ?? normalizedStatus,
    startDate: raw.startDate ? new Date(raw.startDate) : fechaSalida,
    estimatedEndDate: raw.estimatedEndDate ? new Date(raw.estimatedEndDate) : fechaLlegadaEstimada,
    actualEndDate: raw.actualEndDate ? new Date(raw.actualEndDate) : fechaLlegadaReal,
    cargoWeight: raw.cargoWeight ?? raw.peso ?? 0,
    cargoType: raw.cargoType ?? raw.cargoTypeNombre ?? '',
    documents: raw.documents ?? { waybillNumber: '', invoiceNumbers: [], status: 'pendiente' }
  };
}

function hydratePaginated(raw: any): PaginatedTrips {
  const items: Trip[] = Array.isArray(raw?.items) ? raw.items.map(hydrateTrip) : [];
  return { items, total: raw?.total ?? 0 };
}

@Injectable({
  providedIn: 'root'
})
export class TripService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getTrips(page: number = 1, limit: number = 10, search: string = '', statusFilter: TripStatus | 'todos' = 'todos'): Observable<PaginatedTrips> {
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

    return this.http.get<any>(`${this.apiUrl}/trips`, { params }).pipe(
      map(hydratePaginated),
      catchError(() => of({ items: [], total: 0 }))
    );
  }

  getActiveTrips(): Observable<Trip[]> {
    return this.http.get<any>(`${this.apiUrl}/trips`, { params: { page: '1', limit: '1000' } }).pipe(
      map(raw => hydratePaginated(raw).items),
      catchError(() => of([]))
    );
  }

  getTripsForReport(from: Date, to: Date): Observable<TripReportRow[]> {
    const params: Record<string, string> = {
      from: from.toISOString().slice(0, 10),
      to: to.toISOString().slice(0, 10)
    };

    return this.http.get<any>(`${this.apiUrl}/trips`, { params: { ...params, page: '1', limit: '1000' } }).pipe(
      map(raw => {
        const items: Trip[] = hydratePaginated(raw).items;
        const fromTime = new Date(from).setHours(0, 0, 0, 0);
        const toTime = new Date(to).setHours(23, 59, 59, 999);
        return items
          .filter(trip => {
            const time = new Date(trip.fechaSalida).getTime();
            return time >= fromTime && time <= toTime;
          })
          .sort((a, b) => new Date(a.fechaSalida).getTime() - new Date(b.fechaSalida).getTime())
          .map(trip => ({
            id: trip.id,
            origin: trip.origin || trip.origenNombre || '',
            destination: trip.destination || trip.destinoNombre || '',
            conductor: trip.conductorNombre || trip.driver?.name || '',
            fechaSalida: new Date(trip.fechaSalida),
            costoTotal: trip.costoTotal,
            estado: trip.estado
          }));
      }),
      catchError(() => of([]))
    );
  }

  getDeliveredTripsWithoutFulfillment(): Observable<Trip[]> {
    return this.http.get<any>(`${this.apiUrl}/trips`, {
      params: { estado: 'Entregado', without_fulfillment: 'true', page: '1', limit: '1000' }
    }).pipe(
      map(raw => hydratePaginated(raw).items),
      catchError(() => of([]))
    );
  }

  getTripById(tripId: string): Observable<Trip | undefined> {
    return this.http.get<any>(`${this.apiUrl}/trips/${tripId}`).pipe(
      map(raw => hydrateTrip(raw)),
      catchError(() => of(undefined))
    );
  }

  createTrip(trip: Partial<Trip> & { precioPorTon?: number }): Observable<Trip> {
    return this.http.post<any>(`${this.apiUrl}/trips`, trip).pipe(
      map(raw => hydrateTrip(raw)),
      catchError(() => of(hydrateTrip({ ...trip, id: '', estado: 'Programado' })))
    );
  }

  updateTrip(id: string, updates: Partial<Trip>): Observable<Trip> {
    return this.http.put<any>(`${this.apiUrl}/trips/${id}`, updates).pipe(
      map(raw => hydrateTrip(raw)),
      catchError(() => of(hydrateTrip({ id, estado: 'Programado', ...updates })))
    );
  }

  updateTripStatus(tripId: string, newStatus: TripStatus | LegacyTripStatus): Observable<Trip> {
    const normalizedStatus: TripStatus = newStatus === 'Completado' ? 'Entregado' : newStatus as TripStatus;
    return this.http.patch<any>(`${this.apiUrl}/trips/${tripId}/status`, { estado: normalizedStatus }).pipe(
      map(raw => hydrateTrip(raw)),
      catchError(() => of(hydrateTrip({ id: tripId, estado: normalizedStatus })))
    );
  }

  reconcileDocuments(tripId: string): Observable<Trip> {
    return this.http.post<any>(`${this.apiUrl}/trips/${tripId}/reconcile-documents`, {}).pipe(
      map(raw => hydrateTrip(raw)),
      catchError(() => of(hydrateTrip({ id: tripId, estado: 'Programado' })))
    );
  }
}
