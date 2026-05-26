import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { AuthService } from '../../../../core/auth/auth.service';
import { CargoType, CargoTypeService, PaginatedCargoTypes } from '../../../../core/services/cargo-type.service';

@Component({
  selector: 'app-cargo-types',
  templateUrl: './cargo-types.component.html',
  styleUrls: ['./cargo-types.component.css'],
  standalone: false
})
export class CargoTypesComponent implements OnInit {
  cargoTypes: CargoType[] = [];
  total = 0;
  currentPage = 1;
  limit = 5;
  searchTerm = '';
  isLoading = false;
  isModalOpen = false;
  modalMode: 'create' | 'edit' = 'create';
  selectedCargoType: CargoType | null = null;
  userRole = 'operator';

  constructor(
    private cargoTypeService: CargoTypeService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.userRole = this.authService.getUserRole() || 'operator';
    this.loadCargoTypes();
  }

  get isAdmin(): boolean {
    return this.userRole === 'admin';
  }

  loadCargoTypes(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.cargoTypeService.getCargoTypes(this.currentPage, this.limit, this.searchTerm).subscribe({
      next: (result: PaginatedCargoTypes) => {
        this.cargoTypes = result.items;
        this.total = result.total;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando tipos de carga:', error);
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm = input.value;
    this.currentPage = 1;
    this.loadCargoTypes();
  }

  openAddModal(): void {
    if (!this.isAdmin) {
      return;
    }
    this.modalMode = 'create';
    this.selectedCargoType = null;
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  openEditModal(cargoType: CargoType): void {
    if (!this.isAdmin) {
      return;
    }
    this.modalMode = 'edit';
    this.selectedCargoType = { ...cargoType };
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  closeModal(): void {
    this.isModalOpen = false;
    this.selectedCargoType = null;
    this.cdr.markForCheck();
  }

  onCargoTypeSaved(cargoType: CargoType): void {
    if (!this.isAdmin) {
      return;
    }

    if (this.modalMode === 'create') {
      const { id, ...payload } = cargoType;
      this.cargoTypeService.createCargoType(payload).subscribe({
        next: () => {
          this.closeModal();
          this.loadCargoTypes();
        },
        error: (error) => console.error('Error creando carga:', error)
      });
      return;
    }

    if (this.modalMode === 'edit' && this.selectedCargoType) {
      this.cargoTypeService.updateCargoType(this.selectedCargoType.id, cargoType).subscribe({
        next: () => {
          this.closeModal();
          this.loadCargoTypes();
        },
        error: (error) => console.error('Error actualizando carga:', error)
      });
    }
  }

  deleteCargoType(id: string): void {
    if (!this.isAdmin) {
      return;
    }

    if (!confirm('¿Estás seguro de que deseas eliminar este tipo de carga?')) {
      return;
    }

    this.cargoTypeService.deleteCargoType(id).subscribe({
      next: () => this.loadCargoTypes(),
      error: (error) => console.error('Error eliminando carga:', error)
    });
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadCargoTypes();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.getTotalPages()) {
      this.currentPage++;
      this.loadCargoTypes();
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
}
