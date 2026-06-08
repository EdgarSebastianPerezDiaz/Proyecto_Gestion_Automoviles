import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { DashboardService, OperatorDashboardData, KPI, Alert } from '../../../core/services/dashboard.service';
import { TripService, Trip } from '../../../core/services/trip.service';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-operator-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
  standalone: false
})
export class OperatorDashboardComponent implements OnInit {
  dashboardData: OperatorDashboardData | null = null;
  kpis: KPI[] = [];
  alerts: Alert[] = [];
  activeTrips: Trip[] = [];
  isLoading = true;
  errorMessage = '';
  modalOpen = false;

  constructor(
    private dashboardService: DashboardService,
    private tripService: TripService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.isLoading = true;

    // Subscribe independently so each stream can complete and update UI promptly
    this.dashboardService.getOperatorDashboard().subscribe({
      next: (dashboardData) => {
        this.dashboardData = dashboardData || null;
        this.kpis = dashboardData?.kpis || [];
        this.alerts = dashboardData?.alerts || [];
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error loading operator dashboard data:', error);
        this.errorMessage = 'Error al cargar el dashboard';
      }
    });

    this.tripService.getActiveTrips().subscribe({
      next: (trips) => {
        this.activeTrips = trips || [];
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error loading active trips:', error);
        this.errorMessage = 'Error al cargar los viajes activos';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  /**
   * Handle trip status change
   */
  changeStatus(trip: Trip): void {
    const currentStatus = trip.status;
    const newStatus = currentStatus === 'Programado' ? 'En Ruta' : 'Completado';

    this.tripService.updateTripStatus(trip.id, newStatus).subscribe({
      next: () => {
        alert(`Viaje ${trip.id} actualizado a ${newStatus}`);
        trip.status = newStatus as any;
      },
      error: (error: any) => {
        console.error('Error updating trip status:', error);
        alert('Error al actualizar el viaje');
      }
    });
  }

  /**
   * View trip documents
   */
  viewDocuments(trip: Trip): void {
    alert(`Documentos del viaje ${trip.id}:\n\nGuía: ${trip.documents.waybillNumber}\nFacturas: ${trip.documents.invoiceNumbers.join(', ')}\nEstado: ${trip.documents.status}`);
  }

  /**
   * Navigate to all trips view
   */
  viewAllTrips(): void {
    this.router.navigate(['/operator/trips']);
  }

  /**
   * Handle alert click
   */
  handleAlertClick(link?: string): void {
    if (link) {
      this.router.navigate([link]);
    } else {
      alert('Funcionalidad próxima');
    }
  }

  /**
   * Get status badge color
   */
  getStatusColor(status: string): string {
    switch (status) {
      case 'Completado':
        return 'bg-green-100 text-green-800';
      case 'En Ruta':
        return 'bg-blue-100 text-blue-800';
      case 'Programado':
        return 'bg-yellow-100 text-yellow-800';
      case 'Cancelado':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  /**
   * Get severity badge color
   */
  getSeverityColor(severity: string): string {
    switch (severity) {
      case 'error':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'info':
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300';
    }
  }

  /**
   * Format timestamp to relative time
   */
  formatTime(date: Date): string {
    const diff = Date.now() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Hace un momento';
    if (minutes < 60) return `Hace ${minutes}m`;
    if (hours < 24) return `Hace ${hours}h`;
    if (days < 7) return `Hace ${days}d`;
    return new Date(date).toLocaleDateString('es-CO');
  }

  /**
   * Format route display
   */
  formatRoute(origin: string, destination: string): string {
    return `${origin} → ${destination}`;
  }

  openModal(): void {
    this.modalOpen = true;
  }

  closeModal(): void {
    this.modalOpen = false;
  }

  getCurrentDate(): string {
    const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
    const months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    
    const now = new Date();
    const dayName = days[now.getDay()];
    const dayNum = now.getDate();
    const monthName = months[now.getMonth()];
    const year = now.getFullYear();

    return `${dayName} ${dayNum} de ${monthName} de ${year}`;
  }
}
