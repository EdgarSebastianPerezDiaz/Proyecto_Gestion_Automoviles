import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

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

@Injectable({
  providedIn: 'root'
})
export class DashboardService {

  constructor() { }

  /**
   * Get admin dashboard data with KPIs and alerts
   */
  getAdminDashboard(): Observable<AdminDashboardData> {
    const mockData: AdminDashboardData = {
      kpis: [
        {
          label: 'Viajes Activos',
          value: 8,
          icon: '🚚',
          color: 'gold'
        },
        {
          label: 'Viajes Completados',
          value: 47,
          icon: '✅',
          color: 'green'
        },
        {
          label: 'Ingresos del Mes',
          value: '$48.2M',
          unit: 'COP',
          icon: '💰',
          color: 'green'
        },
        {
          label: 'Cumplidos Pendientes',
          value: 5,
          icon: '📋',
          color: 'red'
        },
        {
          label: 'Docs. por Vencer',
          value: 3,
          icon: '⚠️',
          color: 'orange'
        },
        {
          label: 'Vehículos Disponibles',
          value: '12 / 20',
          icon: '🚙',
          color: 'blue'
        }
      ],
      alerts: [
        {
          id: '1',
          severity: 'error',
          message: 'Licencia de Sebastián Torres vence en 12 días',
          link: '/admin/drivers',
          timestamp: new Date()
        },
        {
          id: '2',
          severity: 'warning',
          message: 'SOAT de vehículo ABC456 vence en 25 días',
          link: '/admin/vehicles',
          timestamp: new Date(Date.now() - 3600000)
        },
        {
          id: '3',
          severity: 'warning',
          message: '5 cumplidos pendientes de pago — revisar cartera',
          link: '/admin/invoices',
          timestamp: new Date(Date.now() - 7200000)
        },
        {
          id: '4',
          severity: 'info',
          message: '8 vehículos disponibles para asignación inmediata',
          link: '/admin/vehicles',
          timestamp: new Date(Date.now() - 86400000)
        }
      ]
    };

    return of(mockData);
  }

  /**
   * Get operator dashboard data
   */
  getOperatorDashboard(): Observable<OperatorDashboardData> {
    const mockData: OperatorDashboardData = {
      kpis: [
        {
          label: 'Viajes Activos Hoy',
          value: 8,
          icon: '🚚',
          color: 'gold'
        },
        {
          label: 'Cumplidos por Registrar',
          value: 3,
          icon: '📋',
          color: 'red'
        },
        {
          label: 'Alertas de Documentos',
          value: 3,
          icon: '⚠️',
          color: 'orange'
        },
        {
          label: 'Vehículos Disponibles',
          value: '12 / 20',
          icon: '🚙',
          color: 'blue'
        }
      ],
      alerts: [
        {
          id: '1',
          severity: 'error',
          message: 'VJ-003 fue entregado — registrar cumplido pendiente',
          link: '/operator/fulfillments',
          timestamp: new Date()
        },
        {
          id: '2',
          severity: 'warning',
          message: 'Licencia de Sebastián Torres vence en 12 días — verificar renovación',
          link: '/operator/drivers',
          timestamp: new Date(Date.now() - 3600000)
        },
        {
          id: '3',
          severity: 'warning',
          message: 'SOAT de vehículo ABC456 vence en 25 días — notificar al propietario',
          link: '/operator/vehicles',
          timestamp: new Date(Date.now() - 7200000)
        }
      ]
    };

    return of(mockData).pipe(delay(300));
  }
}
