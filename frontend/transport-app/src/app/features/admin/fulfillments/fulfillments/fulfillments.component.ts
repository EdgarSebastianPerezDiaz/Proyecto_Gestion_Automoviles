import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../../../core/auth/auth.service';
import { Fulfillment, FulfillmentPaymentStatus, FulfillmentService } from '../../../../core/services/fulfillment.service';

@Component({
  selector: 'app-fulfillments',
  templateUrl: './fulfillments.component.html',
  styleUrls: ['./fulfillments.component.css'],
  standalone: false
})
export class FulfillmentsComponent implements OnInit {
  fulfillments: Fulfillment[] = [];
  total = 0;
  currentPage = 1;
  limit = 5;
  searchTerm = '';
  estadoPagoFilter: FulfillmentPaymentStatus | 'todos' = 'todos';
  isLoading = false;
  userRole = 'operator';

  isFormModalOpen = false;
  isDetailsModalOpen = false;
  isPaymentModalOpen = false;
  selectedFulfillment: Fulfillment | null = null;
  selectedTripId = '';

  constructor(
    private authService: AuthService,
    private fulfillmentService: FulfillmentService
  ) {}

  ngOnInit(): void {
    this.userRole = this.authService.getUserRole() || 'operator';
    this.loadFulfillments();
  }

  get isAdmin(): boolean {
    return this.userRole === 'admin';
  }

  loadFulfillments(): void {
    this.isLoading = true;

    this.fulfillmentService.getFulfillments(this.currentPage, this.limit, this.searchTerm, this.estadoPagoFilter).subscribe({
      next: (result) => {
        this.fulfillments = result.items;
        this.total = result.total;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error cargando cumplidos:', error);
        this.isLoading = false;
      }
    });
  }

  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm = input.value;
    this.currentPage = 1;
    this.loadFulfillments();
  }

  onFilterChange(filter: FulfillmentPaymentStatus | 'todos'): void {
    this.estadoPagoFilter = filter;
    this.currentPage = 1;
    this.loadFulfillments();
  }

  openCreateModal(tripId: string = ''): void {
    this.selectedTripId = tripId;
    this.isFormModalOpen = true;
  }

  closeFormModal(): void {
    this.isFormModalOpen = false;
    this.selectedTripId = '';
  }

  onFulfillmentSaved(): void {
    this.closeFormModal();
    this.closePaymentModal();
    this.loadFulfillments();
  }

  openDetailsModal(fulfillment: Fulfillment): void {
    this.selectedFulfillment = fulfillment;
    this.isDetailsModalOpen = true;
  }

  closeDetailsModal(): void {
    this.isDetailsModalOpen = false;
    this.selectedFulfillment = null;
  }

  openPaymentModal(fulfillment: Fulfillment): void {
    if (!this.isAdmin || fulfillment.estadoPago === 'Pagado') {
      return;
    }

    this.selectedFulfillment = fulfillment;
    this.isPaymentModalOpen = true;
  }

  closePaymentModal(): void {
    this.isPaymentModalOpen = false;
    this.selectedFulfillment = null;
  }

  deleteFulfillment(fulfillment: Fulfillment): void {
    if (!this.isAdmin) {
      return;
    }

    if (!confirm(`¿Eliminar el cumplido ${fulfillment.numero}?`)) {
      return;
    }

    this.fulfillmentService.deleteFulfillment(fulfillment.id).subscribe({
      next: () => this.loadFulfillments(),
      error: (error) => console.error('Error eliminando cumplido:', error)
    });
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadFulfillments();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.getTotalPages()) {
      this.currentPage++;
      this.loadFulfillments();
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

  getStatusClass(status: FulfillmentPaymentStatus): string {
    return status === 'Pagado'
      ? 'badge-success'
      : 'badge-warning';
  }
}
