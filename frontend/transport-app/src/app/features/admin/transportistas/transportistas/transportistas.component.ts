import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { Transportista, TransportistaService } from '../../../../core/services/transportista.service';

@Component({
  selector: 'app-transportistas',
  templateUrl: './transportistas.component.html',
  styleUrls: ['./transportistas.component.css'],
  standalone: false
})
export class TransportistasComponent implements OnInit {
  transportistas: Transportista[] = [];
  allTransportistas: Transportista[] = [];
  totalTransportistas = 0;
  searchTerm = '';
  currentPage = 1;
  limit = 5;
  isLoading = false;

  isModalOpen = false;
  modalMode: 'create' | 'edit' = 'create';
  selectedTransportista: Transportista | null = null;

  constructor(
    private transportistaService: TransportistaService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadTransportistas();
  }

  loadTransportistas(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.transportistaService.getAll().subscribe({
      next: (items) => {
        this.allTransportistas = items;
        this.applyFilters();
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando ETransportista:', error);
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm = input.value;
    this.currentPage = 1;
    this.applyFilters();
  }

  applyFilters(): void {
    const search = this.searchTerm.trim().toLowerCase();
    const filtered = search
      ? this.allTransportistas.filter(transportista =>
          transportista.nombre.toLowerCase().includes(search) ||
          transportista.nit.toLowerCase().includes(search)
        )
      : [...this.allTransportistas];

    this.totalTransportistas = filtered.length;
    const start = (this.currentPage - 1) * this.limit;
    this.transportistas = filtered.slice(start, start + this.limit);
  }

  openAddModal(): void {
    this.modalMode = 'create';
    this.selectedTransportista = null;
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  openEditModal(transportista: Transportista): void {
    this.modalMode = 'edit';
    this.selectedTransportista = { ...transportista };
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  closeModal(): void {
    this.isModalOpen = false;
    this.selectedTransportista = null;
    this.cdr.markForCheck();
  }

  onTransportistaSaved(transportista: Transportista): void {
    if (this.modalMode === 'create') {
      const { id, ...payload } = transportista;
      this.transportistaService.create(payload).subscribe({
        next: () => {
          this.closeModal();
          this.loadTransportistas();
        },
        error: (error) => console.error('Error creando ETransportista:', error)
      });
      return;
    }

    if (this.modalMode === 'edit' && this.selectedTransportista) {
      this.transportistaService.update(this.selectedTransportista.id, transportista).subscribe({
        next: () => {
          this.closeModal();
          this.loadTransportistas();
        },
        error: (error) => console.error('Error actualizando ETransportista:', error)
      });
    }
  }

  deleteTransportista(id: string): void {
    if (!confirm('¿Estás seguro de que deseas eliminar este transportista?')) {
      return;
    }

    this.transportistaService.delete(id).subscribe({
      next: () => this.loadTransportistas(),
      error: (error) => console.error('Error eliminando ETransportista:', error)
    });
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.applyFilters();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.getTotalPages()) {
      this.currentPage++;
      this.applyFilters();
    }
  }

  getTotalPages(): number {
    return Math.max(1, Math.ceil(this.totalTransportistas / this.limit));
  }

  getStartIndex(): number {
    if (this.totalTransportistas === 0) {
      return 0;
    }

    return (this.currentPage - 1) * this.limit + 1;
  }

  getEndIndex(): number {
    if (this.totalTransportistas === 0) {
      return 0;
    }

    return Math.min(this.currentPage * this.limit, this.totalTransportistas);
  }
}
