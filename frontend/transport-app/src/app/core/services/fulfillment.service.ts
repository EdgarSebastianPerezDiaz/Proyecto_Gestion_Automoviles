import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

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

const MOCK_FULFILLMENTS: Fulfillment[] = [
  {
    id: '1',
    numero: 'CUM-001',
    tripId: 'TR-001',
    tripNombre: 'Acerías Paz del Río → Metro de Bogotá S.A.S.',
    cliente: 'Metro de Bogotá S.A.S.',
    fechaEntrega: new Date('2026-06-16'),
    horaEntrega: '09:30',
    recibidoPor: 'Juan Rodríguez',
    observaciones: 'Sin novedad',
    estadoPago: 'Pagado',
    createdAt: new Date('2026-06-16T09:30:00'),
    monto: 8320000
  },
  {
    id: '2',
    numero: 'CUM-002',
    tripId: 'TR-002',
    tripNombre: 'Acerías Paz del Río → Homecenter Sodimac',
    cliente: 'Homecenter Sodimac',
    fechaEntrega: new Date('2026-06-11'),
    horaEntrega: '14:15',
    recibidoPor: 'María González',
    observaciones: 'Retraso por lluvias',
    estadoPago: 'Pendiente',
    createdAt: new Date('2026-06-11T14:15:00'),
    monto: 3960000
  }
];

const REPORT_FULFILLMENTS: Fulfillment[] = [
  {
    id: '3',
    numero: 'CUM-101',
    tripId: 'TR-101',
    tripNombre: 'Bavaria S.A. → Almacenes Éxito S.A.',
    cliente: 'Almacenes Éxito S.A.',
    fechaEntrega: new Date('2026-01-09'),
    horaEntrega: '09:30',
    recibidoPor: 'Laura Díaz',
    observaciones: 'Entregado sin novedad',
    estadoPago: 'Pagado',
    createdAt: new Date('2026-01-09T09:30:00'),
    monto: 8320000
  },
  {
    id: '4',
    numero: 'CUM-102',
    tripId: 'TR-102',
    tripNombre: 'Agropecuaria del Meta → Cencosud',
    cliente: 'Cencosud',
    fechaEntrega: new Date('2026-01-23'),
    horaEntrega: '14:10',
    recibidoPor: 'Pedro Rojas',
    observaciones: 'Esperando soporte documental',
    estadoPago: 'Pendiente',
    createdAt: new Date('2026-01-23T14:10:00'),
    monto: 6080000
  },
  {
    id: '5',
    numero: 'CUM-103',
    tripId: 'TR-103',
    tripNombre: 'Postobón S.A. → Olímpica S.A.',
    cliente: 'Olímpica S.A.',
    fechaEntrega: new Date('2026-02-04'),
    horaEntrega: '08:45',
    recibidoPor: 'Andrés Toro',
    observaciones: 'Pagado al cierre',
    estadoPago: 'Pagado',
    createdAt: new Date('2026-02-04T08:45:00'),
    monto: 7040000
  },
  {
    id: '6',
    numero: 'CUM-104',
    tripId: 'TR-104',
    tripNombre: 'Nestlé de Colombia → Carulla',
    cliente: 'Carulla',
    fechaEntrega: new Date('2026-02-19'),
    horaEntrega: '10:05',
    recibidoPor: 'Martha Ruiz',
    observaciones: 'Pendiente conciliación',
    estadoPago: 'Pendiente',
    createdAt: new Date('2026-02-19T10:05:00'),
    monto: 4200000
  },
  {
    id: '7',
    numero: 'CUM-105',
    tripId: 'TR-105',
    tripNombre: 'Cementos Argos → Homecenter Sodimac',
    cliente: 'Homecenter Sodimac',
    fechaEntrega: new Date('2026-03-06'),
    horaEntrega: '11:20',
    recibidoPor: 'Camilo Pérez',
    observaciones: 'Cobro realizado',
    estadoPago: 'Pagado',
    createdAt: new Date('2026-03-06T11:20:00'),
    monto: 8960000
  },
  {
    id: '8',
    numero: 'CUM-106',
    tripId: 'TR-106',
    tripNombre: 'Acerías Paz del Río → Éxito S.A.',
    cliente: 'Éxito S.A.',
    fechaEntrega: new Date('2026-03-13'),
    horaEntrega: '16:40',
    recibidoPor: 'Diana León',
    observaciones: 'Pendiente de pago',
    estadoPago: 'Pendiente',
    createdAt: new Date('2026-03-13T16:40:00'),
    monto: 7680000
  },
  {
    id: '9',
    numero: 'CUM-107',
    tripId: 'TR-107',
    tripNombre: 'Bavaria S.A. → Surtimax',
    cliente: 'Surtimax',
    fechaEntrega: new Date('2026-03-20'),
    horaEntrega: '07:55',
    recibidoPor: 'José Vargas',
    observaciones: 'Pago confirmado',
    estadoPago: 'Pagado',
    createdAt: new Date('2026-03-20T07:55:00'),
    monto: 6400000
  },
  {
    id: '10',
    numero: 'CUM-108',
    tripId: 'TR-108',
    tripNombre: 'Tecnoquímicas → D1',
    cliente: 'D1',
    fechaEntrega: new Date('2026-01-16'),
    horaEntrega: '13:35',
    recibidoPor: 'Sofía Peña',
    observaciones: 'Pendiente gestión contable',
    estadoPago: 'Pendiente',
    createdAt: new Date('2026-01-16T13:35:00'),
    monto: 3920000
  },
  {
    id: '11',
    numero: 'CUM-109',
    tripId: 'TR-109',
    tripNombre: 'Mondelez → Ara',
    cliente: 'Ara',
    fechaEntrega: new Date('2026-02-28'),
    horaEntrega: '09:05',
    recibidoPor: 'Camila Ríos',
    observaciones: 'Pagado',
    estadoPago: 'Pagado',
    createdAt: new Date('2026-02-28T09:05:00'),
    monto: 9600000
  },
  {
    id: '12',
    numero: 'CUM-110',
    tripId: 'TR-110',
    tripNombre: 'Legrand → Falabella',
    cliente: 'Falabella',
    fechaEntrega: new Date('2026-01-30'),
    horaEntrega: '17:00',
    recibidoPor: 'Nicolás Pardo',
    observaciones: 'Pendiente aprobación',
    estadoPago: 'Pendiente',
    createdAt: new Date('2026-01-30T17:00:00'),
    monto: 5760000
  }
];

@Injectable({
  providedIn: 'root'
})
export class FulfillmentService {
  private fulfillments: Fulfillment[] = MOCK_FULFILLMENTS.map(fulfillment => this.cloneFulfillment(fulfillment));
  private reportFulfillments: Fulfillment[] = REPORT_FULFILLMENTS.map(fulfillment => this.cloneFulfillment(fulfillment));
  private nextId = 3;

  private cloneFulfillment(fulfillment: Fulfillment): Fulfillment {
    return {
      ...fulfillment,
      fechaEntrega: new Date(fulfillment.fechaEntrega),
      createdAt: new Date(fulfillment.createdAt)
    };
  }

  private nextFulfillmentNumber(): string {
    const number = `CUM-${String(this.nextId).padStart(3, '0')}`;
    this.nextId++;
    return number;
  }

  getFulfillmentTripIds(): string[] {
    return this.fulfillments.map(fulfillment => fulfillment.tripId);
  }

  hasFulfillmentForTrip(tripId: string): boolean {
    return this.fulfillments.some(fulfillment => fulfillment.tripId === tripId);
  }

  getFulfillmentByTripId(tripId: string): Observable<Fulfillment | undefined> {
    return of(this.fulfillments.find(fulfillment => fulfillment.tripId === tripId)).pipe(
      delay(250),
      map(fulfillment => fulfillment ? this.cloneFulfillment(fulfillment) : undefined)
    );
  }

  getFulfillments(page: number = 1, limit: number = 10, search: string = '', estadoPagoFilter: FulfillmentPaymentStatus | 'todos' = 'todos'): Observable<PaginatedFulfillments> {
    return of(null).pipe(
      delay(300),
      map(() => {
        let filtered = [...this.fulfillments];

        if (estadoPagoFilter !== 'todos') {
          filtered = filtered.filter(fulfillment => fulfillment.estadoPago === estadoPagoFilter);
        }

        if (search.trim()) {
          const term = search.toLowerCase().trim();
          filtered = filtered.filter(fulfillment =>
            fulfillment.numero.toLowerCase().includes(term) ||
            fulfillment.tripId.toLowerCase().includes(term) ||
            fulfillment.tripNombre.toLowerCase().includes(term)
          );
        }

        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit).map(fulfillment => this.cloneFulfillment(fulfillment));

        return { items, total };
      })
    );
  }

  getFulfillmentsForReport(from: Date, to: Date): Observable<Fulfillment[]> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const fromTime = new Date(from).setHours(0, 0, 0, 0);
        const toTime = new Date(to).setHours(23, 59, 59, 999);
        return [...this.fulfillments, ...this.reportFulfillments]
          .filter(fulfillment => {
            const time = new Date(fulfillment.fechaEntrega).getTime();
            return time >= fromTime && time <= toTime;
          })
          .sort((a, b) => a.fechaEntrega.getTime() - b.fechaEntrega.getTime())
          .map(fulfillment => this.cloneFulfillment(fulfillment));
      })
    );
  }

  getFulfillmentById(id: string): Observable<Fulfillment | undefined> {
    return of(this.fulfillments.find(fulfillment => fulfillment.id === id)).pipe(
      delay(250),
      map(fulfillment => fulfillment ? this.cloneFulfillment(fulfillment) : undefined)
    );
  }

  createFulfillment(input: FulfillmentCreateInput): Observable<Fulfillment> {
    return of(null).pipe(
      delay(300),
      map(() => {
        if (this.hasFulfillmentForTrip(input.tripId)) {
          throw new Error(`Ya existe un cumplido para el viaje ${input.tripId}`);
        }

        const created: Fulfillment = {
          id: String(this.nextId),
          numero: this.nextFulfillmentNumber(),
          tripId: input.tripId,
          tripNombre: input.tripNombre,
          fechaEntrega: new Date(input.fechaEntrega),
          horaEntrega: input.horaEntrega,
          recibidoPor: input.recibidoPor,
          observaciones: input.observaciones,
          estadoPago: input.estadoPago || 'Pendiente',
          createdAt: new Date()
        };

        this.fulfillments.push(created);
        return this.cloneFulfillment(created);
      })
    );
  }

  updateFulfillment(id: string, updates: FulfillmentUpdateInput): Observable<Fulfillment> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.fulfillments.findIndex(fulfillment => fulfillment.id === id);
        if (index === -1) {
          throw new Error(`Fulfillment with id ${id} not found`);
        }

        const current = this.fulfillments[index];
        const updated: Fulfillment = {
          ...current,
          observaciones: updates.observaciones ?? current.observaciones,
          estadoPago: updates.estadoPago ?? current.estadoPago
        };

        this.fulfillments[index] = updated;
        return this.cloneFulfillment(updated);
      })
    );
  }

  markAsPaid(id: string): Observable<Fulfillment> {
    return this.updateFulfillment(id, { estadoPago: 'Pagado' });
  }

  deleteFulfillment(id: string): Observable<void> {
    return of(null).pipe(
      delay(250),
      map(() => {
        const index = this.fulfillments.findIndex(fulfillment => fulfillment.id === id);
        if (index > -1) {
          this.fulfillments.splice(index, 1);
        }
      })
    );
  }
}