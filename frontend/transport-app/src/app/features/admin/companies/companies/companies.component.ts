import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CompanyService, Company } from '../../../../core/services/company.service';

@Component({
  selector: 'app-companies',
  templateUrl: './companies.component.html',
  styleUrls: ['./companies.component.css'],
  standalone: false
})
export class CompaniesComponent implements OnInit {
  companies: Company[] = [];
  filteredCompanies: Company[] = [];
  totalCompanies: number = 0;
  searchTerm: string = '';
  currentPage: number = 1;
  limit: number = 5;
  isLoading: boolean = false;

  isModalOpen: boolean = false;
  modalMode: 'create' | 'edit' = 'create';
  selectedCompany?: Company;

  constructor(
    private companyService: CompanyService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadCompanies();
  }

  /**
   * Carga la lista de empresas con paginación
   */
  loadCompanies(): void {
    this.isLoading = true;
    this.cdr.markForCheck();
    this.companyService.getCompanies(this.currentPage, this.limit, this.searchTerm).subscribe({
      next: (result) => {
        this.companies = result.items;
        this.totalCompanies = result.total;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error cargando empresas:', err);
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Maneja el evento de búsqueda
   */
  onSearch(event: any): void {
    this.searchTerm = event.target.value;
    this.currentPage = 1; // Reiniciar a primera página
    this.loadCompanies();
  }

  /**
   * Abre el modal en modo crear
   */
  openAddModal(): void {
    this.modalMode = 'create';
    this.selectedCompany = undefined;
    this.isModalOpen = true;
  }

  /**
   * Abre el modal en modo editar
   */
  openEditModal(company: Company): void {
    this.modalMode = 'edit';
    this.selectedCompany = company;
    this.isModalOpen = true;
  }

  /**
   * Cierra el modal
   */
  closeModal(): void {
    this.isModalOpen = false;
    this.selectedCompany = undefined;
  }

  /**
   * Maneja el evento de guardar empresa (crear o editar)
   */
  onCompanySaved(company: Company): void {
    if (this.modalMode === 'create') {
      this.companyService.createCompany({
        nombre: company.nombre,
        nit: company.nit,
        direccion: company.direccion,
        telefono: company.telefono,
        correo: company.correo
      }).subscribe({
        next: () => {
          this.closeModal();
          this.loadCompanies();
        },
        error: (err) => console.error('Error creando empresa:', err)
      });
    } else if (this.modalMode === 'edit' && this.selectedCompany) {
      this.companyService.updateCompany(this.selectedCompany.id, company).subscribe({
        next: () => {
          this.closeModal();
          this.loadCompanies();
        },
        error: (err) => console.error('Error actualizando empresa:', err)
      });
    }
  }

  /**
   * Elimina una empresa
   */
  deleteCompany(id: string): void {
    if (confirm('¿Estás seguro de que deseas eliminar esta empresa?')) {
      this.companyService.deleteCompany(id).subscribe({
        next: () => {
          this.loadCompanies();
        },
        error: (err) => console.error('Error eliminando empresa:', err)
      });
    }
  }

  /**
   * Cambia a la página anterior
   */
  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadCompanies();
    }
  }

  /**
   * Cambia a la siguiente página
   */
  nextPage(): void {
    const totalPages = Math.ceil(this.totalCompanies / this.limit);
    if (this.currentPage < totalPages) {
      this.currentPage++;
      this.loadCompanies();
    }
  }

  /**
   * Retorna el número total de páginas
   */
  getTotalPages(): number {
    return Math.ceil(this.totalCompanies / this.limit);
  }

  /**
   * Retorna el rango de registros mostrados
   */
  getRecordRange(): string {
    const start = (this.currentPage - 1) * this.limit + 1;
    const end = Math.min(this.currentPage * this.limit, this.totalCompanies);
    return `${start} - ${end}`;
  }

  /**
   * Verifica si hay página siguiente
   */
  hasNextPage(): boolean {
    return this.currentPage < this.getTotalPages();
  }

  /**
   * Verifica si hay página anterior
   */
  hasPreviousPage(): boolean {
    return this.currentPage > 1;
  }
}
