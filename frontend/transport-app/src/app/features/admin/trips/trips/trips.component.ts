import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { AuthService } from '../../../../core/auth/auth.service';
import { Trip, TripService, TripStatus } from '../../../../core/services/trip.service';

@Component({
  selector: 'app-trips',
  templateUrl: './trips.component.html',
  styleUrls: ['./trips.component.css'],
  standalone: false
})
export class TripsComponent implements OnInit {
  trips: Trip[] = [];
  total = 0;
  currentPage = 1;
  limit = 5;
  searchTerm = '';
  statusFilter: TripStatus | 'todos' = 'todos';
  isLoading = false;
  userRole = 'operator';

  isWizardOpen = false;
  wizardMode: 'create' | 'edit' = 'create';
  selectedTrip: Trip | null = null;

  isStatusModalOpen = false;
  isDocumentsModalOpen = false;
  documentsTripId = '';
  changeStatusTrip: Trip | null = null;

  constructor(
    private tripService: TripService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.userRole = this.authService.getUserRole() || 'operator';
    this.loadTrips();
  }

  get isAdmin(): boolean {
    return this.userRole === 'admin';
  }

  loadTrips(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.tripService.getTrips(this.currentPage, this.limit, this.searchTerm, this.statusFilter).subscribe({
      next: (result) => {
        this.trips = result.items;
        this.total = result.total;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando viajes:', error);
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm = input.value;
    this.currentPage = 1;
    this.loadTrips();
  }

  onFilterChange(status: TripStatus | 'todos'): void {
    this.statusFilter = status;
    this.currentPage = 1;
    this.loadTrips();
  }

  openAddModal(): void {
    if (!this.isAdmin) {
      return;
    }
    this.wizardMode = 'create';
    this.selectedTrip = null;
    this.isWizardOpen = true;
    this.cdr.markForCheck();
  }

  openEditModal(trip: Trip): void {
    if (!this.isAdmin) {
      return;
    }
    this.wizardMode = 'edit';
    this.selectedTrip = { ...trip };
    this.isWizardOpen = true;
    this.cdr.markForCheck();
  }

  closeWizard(): void {
    this.isWizardOpen = false;
    this.selectedTrip = null;
    this.cdr.markForCheck();
  }

  onTripSaved(): void {
    this.closeWizard();
    this.loadTrips();
  }

  openStatusModal(trip: Trip): void {
    if (!this.isAdmin) {
      return;
    }
    this.changeStatusTrip = trip;
    this.isStatusModalOpen = true;
    this.cdr.markForCheck();
  }

  closeStatusModal(): void {
    this.isStatusModalOpen = false;
    this.changeStatusTrip = null;
    this.cdr.markForCheck();
  }

  onStatusChanged(newStatus: TripStatus): void {
    if (!this.changeStatusTrip) {
      return;
    }

    this.tripService.updateTripStatus(this.changeStatusTrip.id, newStatus).subscribe({
      next: () => {
        this.closeStatusModal();
        this.loadTrips();
      },
      error: (error) => console.error('Error actualizando estado del viaje:', error)
    });
  }

  openDocumentsModal(trip: Trip): void {
    this.documentsTripId = trip.id;
    this.isDocumentsModalOpen = true;
    this.cdr.markForCheck();
  }

  closeDocumentsModal(): void {
    this.isDocumentsModalOpen = false;
    this.documentsTripId = '';
    this.cdr.markForCheck();
  }

  cancelTrip(trip: Trip): void {
    if (!this.isAdmin) {
      return;
    }

    if (trip.estado !== 'Programado' && trip.estado !== 'En Ruta') {
      return;
    }

    if (!confirm(`¿Estás seguro de que deseas cancelar el viaje ${trip.id}?`)) {
      return;
    }

    this.tripService.updateTripStatus(trip.id, 'Cancelado').subscribe({
      next: () => this.loadTrips(),
      error: (error) => console.error('Error cancelando viaje:', error)
    });
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadTrips();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.getTotalPages()) {
      this.currentPage++;
      this.loadTrips();
    }
  }

  getTotalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.limit));
  }

  getStartIndex(): number {
    if (this.total === 0) {
      return 0;
    }
    return (this.currentPage - 1) * this.limit + 1;
  }

  getEndIndex(): number {
    if (this.total === 0) {
      return 0;
    }
    return Math.min(this.currentPage * this.limit, this.total);
  }

  getStatusClass(status: TripStatus): string {
    switch (status) {
      case 'Programado':
        return 'badge-info';
      case 'En Ruta':
        return 'badge-success';
      case 'Entregado':
        return 'badge-warning';
      case 'Cancelado':
      default:
        return 'badge-danger';
    }
  }

  getAllowedStatuses(currentStatus: TripStatus): TripStatus[] {
    switch (currentStatus) {
      case 'Programado':
        return ['En Ruta', 'Cancelado'];
      case 'En Ruta':
        return ['Entregado', 'Cancelado'];
      default:
        return [];
    }
  }
}
