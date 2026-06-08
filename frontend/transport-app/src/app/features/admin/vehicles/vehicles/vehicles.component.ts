import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { DriverService } from '../../../../core/services/driver.service';
import { TransportistaService } from '../../../../core/services/transportista.service';
import { Vehicle, VehicleService, VehicleStatusFilter } from '../../../../core/services/vehicle.service';

@Component({
  selector: 'app-vehicles',
  templateUrl: './vehicles.component.html',
  styleUrls: ['./vehicles.component.css'],
  standalone: false
})
export class VehiclesComponent implements OnInit {
  vehicles: Vehicle[] = [];
  totalVehicles = 0;
  currentPage = 1;
  limit = 5;
  searchTerm = '';
  statusFilter: VehicleStatusFilter = 'todos';
  isLoading = false;

  isModalOpen = false;
  modalMode: 'create' | 'edit' = 'create';
  selectedVehicle: Vehicle | null = null;

  constructor(
    private vehicleService: VehicleService,
    private transportistaService: TransportistaService,
    private driverService: DriverService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadVehicles();
  }

  loadVehicles(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.vehicleService.getVehicles(this.currentPage, this.limit, this.searchTerm, this.statusFilter).subscribe({
      next: (result) => {
        forkJoin({
          transportistas: this.transportistaService.getAll(),
          drivers: this.driverService.getDrivers(1, 1000, '')
        }).subscribe({
          next: ({ transportistas, drivers }) => {
            this.vehicles = result.items.map((vehicle) => ({
              ...vehicle,
              transportistaNombre: transportistas.find(item => item.id === vehicle.transportistaId)?.nombre || 'Sin transportista',
              conductorNombre: drivers.items.find(item => item.id === vehicle.conductorId)?.fullName || 'Sin conductor'
            }));
            this.totalVehicles = result.total;
            this.isLoading = false;
            this.cdr.markForCheck();
          },
          error: (error) => {
            console.error('Error enriqueciendo vehículos:', error);
            this.vehicles = result.items;
            this.totalVehicles = result.total;
            this.isLoading = false;
            this.cdr.markForCheck();
          }
        });
      },
      error: (error) => {
        console.error('Error cargando vehículos:', error);
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm = input.value;
    this.currentPage = 1;
    this.loadVehicles();
  }

  onFilterChange(status: VehicleStatusFilter): void {
    this.statusFilter = status;
    this.currentPage = 1;
    this.loadVehicles();
  }

  openAddModal(): void {
    this.modalMode = 'create';
    this.selectedVehicle = null;
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  openEditModal(vehicle: Vehicle): void {
    this.modalMode = 'edit';
    this.selectedVehicle = { ...vehicle };
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  closeModal(): void {
    this.isModalOpen = false;
    this.selectedVehicle = null;
    this.cdr.markForCheck();
  }

  onVehicleSaved(vehicle: Vehicle): void {
    if (this.modalMode === 'create') {
      const { id, transportistaNombre, conductorNombre, ...createPayload } = vehicle;
      this.vehicleService.createVehicle(createPayload).subscribe({
        next: () => {
          this.closeModal();
          this.loadVehicles();
        },
        error: (error) => console.error('Error creando vehículo:', error)
      });
      return;
    }

    if (this.modalMode === 'edit' && this.selectedVehicle) {
      const { transportistaNombre, conductorNombre, ...updatePayload } = vehicle;
      this.vehicleService.updateVehicle(this.selectedVehicle.id, updatePayload).subscribe({
        next: () => {
          this.closeModal();
          this.loadVehicles();
        },
        error: (error) => console.error('Error actualizando vehículo:', error)
      });
    }
  }

  deleteVehicle(id: string): void {
    if (!confirm('¿Estás seguro de que deseas eliminar este vehículo?')) {
      return;
    }

    this.vehicleService.deleteVehicle(id).subscribe({
      next: () => this.loadVehicles(),
      error: (error) => console.error('Error eliminando vehículo:', error)
    });
  }

  previousPage(): void {
    if (this.hasPreviousPage()) {
      this.currentPage--;
      this.loadVehicles();
    }
  }

  nextPage(): void {
    if (this.hasNextPage()) {
      this.currentPage++;
      this.loadVehicles();
    }
  }

  getTotalPages(): number {
    return Math.max(1, Math.ceil(this.totalVehicles / this.limit));
  }

  getStartIndex(): number {
    if (this.totalVehicles === 0) {
      return 0;
    }

    return (this.currentPage - 1) * this.limit + 1;
  }

  getEndIndex(): number {
    if (this.totalVehicles === 0) {
      return 0;
    }

    return Math.min(this.currentPage * this.limit, this.totalVehicles);
  }

  hasPreviousPage(): boolean {
    return this.currentPage > 1;
  }

  hasNextPage(): boolean {
    return this.currentPage < this.getTotalPages();
  }

  getStatusBadgeClass(status: Vehicle['estado']): string {
    switch (status) {
      case 'Disponible':
        return 'badge-success';
      case 'En Viaje':
        return 'badge-info';
      case 'Inactivo':
      default:
        return 'badge-warning';
    }
  }
}
