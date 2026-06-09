import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface KPI {
  label: string;
  value: string | number;
  unit?: string;
  icon: string;
  color: string;
}

export interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'error';
  message: string;
  link?: string;
  timestamp: Date;
}

export interface AdminDashboardData {
  kpis: KPI[];
  alerts: Alert[];
}

export interface OperatorDashboardData {
  kpis: KPI[];
  alerts: Alert[];
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getAdminDashboard(): Observable<AdminDashboardData> {
    return forkJoin({
      trips: this.http
        .get<{ items: any[]; total: number }>(`${this.apiUrl}/trips`, {
          params: { page: '1', limit: '1000' },
        })
        .pipe(catchError(() => of({ items: [], total: 0 }))),
      vehicles: this.http
        .get<{ items: any[]; total: number }>(`${this.apiUrl}/vehicles`, {
          params: { page: '1', limit: '1000' },
        })
        .pipe(catchError(() => of({ items: [], total: 0 }))),
      drivers: this.http
        .get<{ items: any[]; total: number }>(`${this.apiUrl}/drivers`, {
          params: { page: '1', limit: '1000' },
        })
        .pipe(catchError(() => of({ items: [], total: 0 }))),
      invoices: this.http
        .get<{ items: any[]; total: number }>(`${this.apiUrl}/invoices`, {
          params: { page: '1', limit: '1000' },
        })
        .pipe(catchError(() => of({ items: [], total: 0 }))),
    }).pipe(
      map(({ trips, vehicles, drivers, invoices }) => {
        const allTrips = trips.items || [];
        const allVehicles = vehicles.items || [];
        const allDrivers = drivers.items || [];
        const allInvoices = invoices.items || [];

        const activeTrips = allTrips.filter((t: any) => t.estado === 'En Ruta').length;
        const completedTrips = allTrips.filter((t: any) => t.estado === 'Entregado').length;
        const availableVehicles = allVehicles.filter((v: any) => v.estado === 'Disponible').length;
        const pendingInvoices = allInvoices.filter((i: any) => i.estado === 'Pendiente').length;
        const today = new Date();
        const in30days = new Date(today.getTime() + 30 * 86400000);
        const expiringDrivers = allDrivers.filter((d: any) => {
          const exp = d.license_expiry ? new Date(d.license_expiry) : null;
          return exp && exp > today && exp < in30days;
        }).length;

        const kpis: KPI[] = [
          { label: 'Viajes Activos', value: activeTrips, icon: '🚚', color: 'gold' },
          { label: 'Viajes Completados', value: completedTrips, icon: '✅', color: 'green' },
          { label: 'Cumplidos Pendientes', value: pendingInvoices, icon: '📋', color: 'red' },
          { label: 'Docs. por Vencer', value: expiringDrivers, icon: '⚠️', color: 'orange' },
          {
            label: 'Vehículos Disponibles',
            value: `${availableVehicles} / ${allVehicles.length}`,
            icon: '🚙',
            color: 'blue',
          },
        ];

        const alerts: Alert[] = [];
        if (expiringDrivers > 0) {
          alerts.push({
            id: 'drv-exp',
            severity: 'warning',
            message: `${expiringDrivers} licencia(s) de conductor por vencer en 30 días`,
            link: '/admin/drivers',
            timestamp: new Date(),
          });
        }
        if (pendingInvoices > 0) {
          alerts.push({
            id: 'inv-pending',
            severity: 'info',
            message: `${pendingInvoices} cumplidos pendientes de pago`,
            link: '/admin/invoices',
            timestamp: new Date(),
          });
        }

        return { kpis, alerts };
      })
    );
  }

  getOperatorDashboard(): Observable<OperatorDashboardData> {
    return this.getAdminDashboard().pipe(
      map(data => ({
        kpis: data.kpis.filter(k =>
          ['Viajes Activos', 'Cumplidos Pendientes', 'Docs. por Vencer', 'Vehículos Disponibles'].includes(k.label)
        ),
        alerts: data.alerts,
      }))
    );
  }
}
