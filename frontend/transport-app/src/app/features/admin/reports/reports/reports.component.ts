import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ExportService } from '../../../../core/services/export.service';
import { Fulfillment, FulfillmentService } from '../../../../core/services/fulfillment.service';
import { TripReportRow, TripService } from '../../../../core/services/trip.service';

type ReportsTab = 'trips' | 'financial';

interface TripReportViewRow {
  idViaje: string;
  ruta: string;
  conductor: string;
  fechaSalida: Date;
  costoTotal: number;
  estado: string;
}

interface FinancialReportViewRow {
  numeroCumplido: string;
  viajeAsociado: string;
  cliente: string;
  fechaEntrega: Date;
  montoPendiente: number;
  estadoPago: string;
}

@Component({
  selector: 'app-reports',
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.css'],
  standalone: false
})
export class ReportsComponent implements OnInit {
  activeTab: ReportsTab = 'trips';
  fromDate = '2026-01-01';
  toDate = new Date().toISOString().slice(0, 10);
  Math = Math;

  tripsRows: TripReportViewRow[] = [];
  financialRows: FinancialReportViewRow[] = [];

  tripsKpis = [
    { label: 'Total Viajes', value: 0, color: 'gold' },
    { label: 'Viajes Completados', value: 0, color: 'green' },
    { label: 'Viajes En Ruta', value: 0, color: 'blue' },
    { label: 'Viajes Cancelados', value: 0, color: 'red' }
  ];

  financialKpis = [
    { label: 'Ingresos Totales', value: 0, color: 'gold' },
    { label: 'Cumplidos Pagados', value: 0, color: 'green' },
    { label: 'Cumplidos Pendientes', value: 0, color: 'orange' },
    { label: 'Cartera Pendiente', value: 0, color: 'red' }
  ];

  constructor(
    private tripService: TripService,
    private fulfillmentService: FulfillmentService,
    private exportService: ExportService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.generateReport();
  }

  switchTab(tab: ReportsTab): void {
    this.activeTab = tab;
    this.cdr.detectChanges();
  }

  generateReport(): void {
    this.loadTripsReport();
    this.loadFinancialReport();
  }

  loadTripsReport(): void {
    const from = new Date(this.fromDate);
    const to = new Date(this.toDate);

    this.tripService.getTripsForReport(from, to).subscribe((trips: TripReportRow[]) => {
      const mapped = trips.map(trip => ({
        idViaje: trip.id,
        ruta: `${trip.origin} → ${trip.destination}`,
        conductor: trip.conductor,
        fechaSalida: trip.fechaSalida,
        costoTotal: trip.costoTotal,
        estado: trip.estado
      }));

      this.tripsRows = mapped;
      this.tripsKpis = [
        { label: 'Total Viajes', value: mapped.length, color: 'gold' },
        { label: 'Viajes Completados', value: mapped.filter(item => item.estado === 'Entregado').length, color: 'green' },
        { label: 'Viajes En Ruta', value: mapped.filter(item => item.estado === 'En Ruta').length, color: 'blue' },
        { label: 'Viajes Cancelados', value: mapped.filter(item => item.estado === 'Cancelado').length, color: 'red' }
      ];
      this.cdr.detectChanges();
    });
  }

  loadFinancialReport(): void {
    const from = new Date(this.fromDate);
    const to = new Date(this.toDate);

    this.tripService.getTripsForReport(from, to).subscribe((trips: TripReportRow[]) => {
      this.fulfillmentService.getFulfillmentsForReport(from, to).subscribe((fulfillments: Fulfillment[]) => {
        const deliveredTrips = trips.filter(trip => trip.estado === 'Entregado');
        const deliveredMap = new Map(deliveredTrips.map(trip => [trip.id, trip] as const));

        const rows = fulfillments.map(fulfillment => {
          const trip = deliveredMap.get(fulfillment.tripId);
          return {
            numeroCumplido: fulfillment.numero,
            viajeAsociado: fulfillment.tripNombre,
            cliente: fulfillment.cliente || trip?.destination || '',
            fechaEntrega: fulfillment.fechaEntrega,
            montoPendiente: fulfillment.estadoPago === 'Pagado' ? 0 : (fulfillment.monto || trip?.costoTotal || 0),
            estadoPago: fulfillment.estadoPago
          };
        });

        const ingresosTotales = deliveredTrips.reduce((sum, trip) => sum + trip.costoTotal, 0);
        const cumplidosPagados = fulfillments.filter(item => item.estadoPago === 'Pagado').length;
        const cumplidosPendientes = fulfillments.filter(item => item.estadoPago === 'Pendiente').length;
        const carteraPendiente = fulfillments.reduce((sum, item) => sum + (item.estadoPago === 'Pendiente' ? (item.monto || deliveredMap.get(item.tripId)?.costoTotal || 0) : 0), 0);

        this.financialRows = rows;
        this.financialKpis = [
          { label: 'Ingresos Totales', value: ingresosTotales, color: 'gold' },
          { label: 'Cumplidos Pagados', value: cumplidosPagados, color: 'green' },
          { label: 'Cumplidos Pendientes', value: cumplidosPendientes, color: 'orange' },
          { label: 'Cartera Pendiente', value: carteraPendiente, color: 'red' }
        ];
        this.cdr.detectChanges();
      });
    });
  }

  exportCurrentTab(): void {
    if (this.activeTab === 'trips') {
      this.exportService.exportToCSV(
        this.tripsRows.map(row => ({
          'ID Viaje': row.idViaje,
          'Origen - Destino': row.ruta,
          Conductor: row.conductor,
          'Fecha Salida': row.fechaSalida,
          'Costo Total': row.costoTotal,
          Estado: row.estado
        })),
        `reporte-viajes-${new Date().toISOString()}.csv`
      );
    } else {
      this.exportService.exportToCSV(
        this.financialRows.map(row => ({
          'N° Cumplido': row.numeroCumplido,
          'Viaje Asociado': row.viajeAsociado,
          Cliente: row.cliente,
          'Fecha Entrega': row.fechaEntrega,
          'Monto Pendiente': row.montoPendiente,
          'Estado Pago': row.estadoPago
        })),
        `reporte-financiero-${new Date().toISOString()}.csv`
      );
    }
  }
}
