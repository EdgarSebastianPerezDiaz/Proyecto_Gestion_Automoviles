import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { Driver, DriverService, LicenseFilter, PaginatedDrivers } from '../../../../core/services/driver.service';

@Component({
  selector: 'app-drivers',
  templateUrl: './drivers.component.html',
  styleUrls: ['./drivers.component.scss'],
  standalone: false
})
export class DriversComponent implements OnInit {

  drivers: Driver[] = [];
  totalDrivers: number = 0;
  searchTerm: string = '';
  currentPage: number = 1;
  limit: number = 5;
  isLoading: boolean = false;
  isModalOpen: boolean = false;
  modalMode: 'create' | 'edit' = 'create';
  selectedDriver: Driver | null = null;
  licenseFilter: LicenseFilter = 'all';

  // Contador de licencias
  licenseStats = {
    vigentes: 0,
    porVencer: 0,
    vencidas: 0
  };

  constructor(
    private driverService: DriverService,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit(): void {
    this.loadDrivers();
    this.loadLicenseStats();
  }

  /**
   * Cargar conductores
   */
  loadDrivers(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.driverService.getDrivers(this.currentPage, this.limit, this.searchTerm, this.licenseFilter)
      .subscribe({
        next: (result: PaginatedDrivers) => {
          this.drivers = result.items;
          this.totalDrivers = result.total;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err: any) => {
          console.error('Error loading drivers:', err);
          this.isLoading = false;
          this.cdr.markForCheck();
        }
      });
  }

  /**
   * Cargar estadísticas de licencias
   */
  loadLicenseStats(): void {
    this.driverService.getDriverCountByLicenseStatus().subscribe({
      next: (stats: any) => {
        this.licenseStats = stats;
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Buscar conductores
   */
  onSearch(event: any): void {
    this.searchTerm = event.target.value;
    this.currentPage = 1;
    this.loadDrivers();
  }

  /**
   * Aplicar filtro de licencia
   */
  applyLicenseFilter(filter: LicenseFilter): void {
    this.licenseFilter = filter;
    this.currentPage = 1;
    this.loadDrivers();
  }

  /**
   * Obtener estado de licencia con color
   */
  getLicenseStatusBadge(fechaVencimiento: string): { text: string; color: string } {
    const today = new Date();
    const expiryDate = new Date(fechaVencimiento);
    const daysUntilExpiry = Math.floor((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) {
      return { text: 'Vencida', color: 'red' };
    } else if (daysUntilExpiry <= 90) {
      return { text: 'Por Vencer', color: 'yellow' };
    } else {
      return { text: 'Vigente', color: 'green' };
    }
  }

  /**
   * Abrir modal para crear
   */
  openAddModal(): void {
    this.modalMode = 'create';
    this.selectedDriver = null;
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  /**
   * Abrir modal para editar
   */
  openEditModal(driver: Driver): void {
    this.modalMode = 'edit';
    this.selectedDriver = { ...driver };
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  /**
   * Cerrar modal
   */
  closeModal(): void {
    this.isModalOpen = false;
    this.selectedDriver = null;
    this.cdr.markForCheck();
  }

  /**
   * Guardar conductor (crear o editar)
   */
  onDriverSaved(driverData: any): void {
    if (this.modalMode === 'create') {
      this.driverService.createDriver(driverData).subscribe({
        next: () => {
          this.closeModal();
          this.loadDrivers();
          this.loadLicenseStats();
        }
      });
    } else if (this.modalMode === 'edit' && this.selectedDriver) {
      this.driverService.updateDriver(this.selectedDriver.id, driverData).subscribe({
        next: () => {
          this.closeModal();
          this.loadDrivers();
          this.loadLicenseStats();
        }
      });
    }
  }

  /**
   * Eliminar conductor
   */
  deleteDriver(id: string): void {
    if (confirm('¿Estás seguro de que deseas eliminar este conductor?')) {
      this.driverService.deleteDriver(id).subscribe({
        next: () => {
          this.loadDrivers();
          this.loadLicenseStats();
        }
      });
    }
  }

  /**
   * Página anterior
   */
  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadDrivers();
    }
  }

  /**
   * Página siguiente
   */
  nextPage(): void {
    const maxPages = Math.ceil(this.totalDrivers / this.limit);
    if (this.currentPage < maxPages) {
      this.currentPage++;
      this.loadDrivers();
    }
  }

  /**
   * Obtener número total de páginas
   */
  getTotalPages(): number {
    return Math.ceil(this.totalDrivers / this.limit);
  }

  /**
   * Obtener índice de inicio para mostrar
   */
  getStartIndex(): number {
    return (this.currentPage - 1) * this.limit + 1;
  }

  /**
   * Obtener índice de fin para mostrar
   */
  getEndIndex(): number {
    return Math.min(this.getStartIndex() + this.drivers.length - 1, this.totalDrivers);
  }

  /**
   * Verificar si es el badge rojo (vencida)
   */
  isBadgeRed(color: string): boolean {
    return color === 'red';
  }

  /**
   * Verificar si es el badge amarillo (por vencer)
   */
  isBadgeYellow(color: string): boolean {
    return color === 'yellow';
  }

  /**
   * Verificar si es el badge verde (vigente)
   */
  isBadgeGreen(color: string): boolean {
    return color === 'green';
  }

  getLicenseBadgeClass(fechaVencimiento: string): string {
    const badge = this.getLicenseStatusBadge(fechaVencimiento);
    switch (badge.color) {
      case 'green':
        return 'badge-success';
      case 'yellow':
        return 'badge-warning';
      default:
        return 'badge-danger';
    }
  }
}
