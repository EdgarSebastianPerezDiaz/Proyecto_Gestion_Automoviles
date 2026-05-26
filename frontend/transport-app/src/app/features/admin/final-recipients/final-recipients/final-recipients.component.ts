import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FinalRecipient, FinalRecipientService } from '../../../../core/services/final-recipient.service';

@Component({
  selector: 'app-final-recipients',
  templateUrl: './final-recipients.component.html',
  styleUrls: ['./final-recipients.component.css'],
  standalone: false
})
export class FinalRecipientsComponent implements OnInit {
  finalRecipients: FinalRecipient[] = [];
  allFinalRecipients: FinalRecipient[] = [];
  totalFinalRecipients = 0;
  searchTerm = '';
  currentPage = 1;
  limit = 5;
  isLoading = false;

  isModalOpen = false;
  modalMode: 'create' | 'edit' = 'create';
  selectedFinalRecipient: FinalRecipient | null = null;

  constructor(
    private finalRecipientService: FinalRecipientService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadFinalRecipients();
  }

  loadFinalRecipients(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.finalRecipientService.getAll().subscribe({
      next: (items) => {
        this.allFinalRecipients = items;
        this.applyFilters();
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando EDestino:', error);
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
      ? this.allFinalRecipients.filter(recipient =>
          recipient.nombre.toLowerCase().includes(search) ||
          recipient.nit.toLowerCase().includes(search)
        )
      : [...this.allFinalRecipients];

    this.totalFinalRecipients = filtered.length;
    const start = (this.currentPage - 1) * this.limit;
    this.finalRecipients = filtered.slice(start, start + this.limit);
  }

  openAddModal(): void {
    this.modalMode = 'create';
    this.selectedFinalRecipient = null;
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  openEditModal(finalRecipient: FinalRecipient): void {
    this.modalMode = 'edit';
    this.selectedFinalRecipient = { ...finalRecipient };
    this.isModalOpen = true;
    this.cdr.markForCheck();
  }

  closeModal(): void {
    this.isModalOpen = false;
    this.selectedFinalRecipient = null;
    this.cdr.markForCheck();
  }

  onFinalRecipientSaved(finalRecipient: FinalRecipient): void {
    if (this.modalMode === 'create') {
      const { id, ...payload } = finalRecipient;
      this.finalRecipientService.create(payload).subscribe({
        next: () => {
          this.closeModal();
          this.loadFinalRecipients();
        },
        error: (error) => console.error('Error creando EDestino:', error)
      });
      return;
    }

    if (this.modalMode === 'edit' && this.selectedFinalRecipient) {
      this.finalRecipientService.update(this.selectedFinalRecipient.id, finalRecipient).subscribe({
        next: () => {
          this.closeModal();
          this.loadFinalRecipients();
        },
        error: (error) => console.error('Error actualizando EDestino:', error)
      });
    }
  }

  deleteFinalRecipient(id: string): void {
    if (!confirm('¿Estás seguro de que deseas eliminar este destinatario?')) {
      return;
    }

    this.finalRecipientService.delete(id).subscribe({
      next: () => this.loadFinalRecipients(),
      error: (error) => console.error('Error eliminando EDestino:', error)
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
    return Math.max(1, Math.ceil(this.totalFinalRecipients / this.limit));
  }

  getStartIndex(): number {
    if (this.totalFinalRecipients === 0) {
      return 0;
    }

    return (this.currentPage - 1) * this.limit + 1;
  }

  getEndIndex(): number {
    if (this.totalFinalRecipients === 0) {
      return 0;
    }

    return Math.min(this.currentPage * this.limit, this.totalFinalRecipients);
  }
}
