import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export type FulfillmentPaymentStatus = 'Pendiente' | 'Pagado';

export interface Fulfillment {
  id: string;
  numero: string;
  tripId: string;
  tripNombre: string;
  cliente?: string;
  fechaEntrega: Date;
  horaEntrega: string;
  recibidoPor: string;
  observaciones?: string;
  estadoPago: FulfillmentPaymentStatus;
  createdAt: Date;
  monto?: number;
}

export interface PaginatedFulfillments {
  items: Fulfillment[];
  total: number;
}

export interface FulfillmentCreateInput {
  tripId: string;
  tripNombre: string;
  fechaEntrega: Date | string;
  horaEntrega: string;
  recibidoPor: string;
  observaciones?: string;
  estadoPago?: FulfillmentPaymentStatus;
}

export interface FulfillmentUpdateInput {
  observaciones?: string;
  estadoPago?: FulfillmentPaymentStatus;
}

@Injectable({ providedIn: 'root' })
export class FulfillmentService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  private mapItem(raw: any): Fulfillment {
    return {
      ...raw,
      fechaEntrega: new Date(raw.fechaEntrega ?? raw.fecha_entrega),
      createdAt: new Date(raw.createdAt ?? raw.created_at ?? Date.now()),
      estadoPago: raw.estadoPago ?? raw.estado_pago ?? 'Pendiente',
    };
  }

  getFulfillments(
    page = 1,
    limit = 10,
    search = '',
    estadoPago?: FulfillmentPaymentStatus
  ): Observable<PaginatedFulfillments> {
    const params: Record<string, string> = { page: String(page), limit: String(limit) };
    if (search.trim()) params['search'] = search.trim();
    if (estadoPago) params['estadoPago'] = estadoPago;

    return this.http
      .get<PaginatedFulfillments>(`${this.apiUrl}/invoices`, { params })
      .pipe(
        map(r => ({
          items: (r.items || []).map(i => this.mapItem(i)),
          total: r.total || 0,
        })),
        catchError(() => of({ items: [], total: 0 }))
      );
  }

  getFulfillmentById(id: string): Observable<Fulfillment | undefined> {
    return this.http.get<any>(`${this.apiUrl}/invoices/${id}`).pipe(
      map(r => this.mapItem(r)),
      catchError(() => of(undefined))
    );
  }

  createFulfillment(input: FulfillmentCreateInput): Observable<Fulfillment> {
    const body = {
      trip_id: input.tripId,
      trip_nombre: input.tripNombre,
      fecha_entrega: input.fechaEntrega instanceof Date
        ? input.fechaEntrega.toISOString()
        : input.fechaEntrega,
      hora_entrega: input.horaEntrega,
      recibido_por: input.recibidoPor,
      observaciones: input.observaciones,
      estado_pago: input.estadoPago ?? 'Pendiente',
    };

    return this.http.post<any>(`${this.apiUrl}/invoices`, body).pipe(
      map(r => this.mapItem(r)),
      catchError(() =>
        of({
          id: '',
          numero: '',
          tripId: input.tripId,
          tripNombre: input.tripNombre,
          fechaEntrega: input.fechaEntrega instanceof Date ? input.fechaEntrega : new Date(input.fechaEntrega),
          horaEntrega: input.horaEntrega,
          recibidoPor: input.recibidoPor,
          observaciones: input.observaciones,
          estadoPago: input.estadoPago ?? 'Pendiente',
          createdAt: new Date(),
        })
      )
    );
  }

  updateFulfillment(id: string, input: FulfillmentUpdateInput): Observable<Fulfillment> {
    return this.http.put<any>(`${this.apiUrl}/invoices/${id}`, input).pipe(
      map(r => this.mapItem(r)),
      catchError(() =>
        of({
          id,
          numero: '',
          tripId: '',
          tripNombre: '',
          fechaEntrega: new Date(),
          horaEntrega: '',
          recibidoPor: '',
          estadoPago: input.estadoPago ?? 'Pendiente',
          createdAt: new Date(),
        })
      )
    );
  }

  markAsPaid(id: string): Observable<Fulfillment> {
    return this.updateFulfillment(id, { estadoPago: 'Pagado' });
  }

  deleteFulfillment(id: string): Observable<boolean> {
    return this.http.delete<void>(`${this.apiUrl}/invoices/${id}`).pipe(
      map(() => true),
      catchError(() => of(false))
    );
  }

  getPendingCount(): Observable<number> {
    return this.getFulfillments(1, 1, '', 'Pendiente').pipe(map(r => r.total));
  }
}
