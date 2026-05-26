import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { AuthService } from '../../../../core/auth/auth.service';
import { Trip, TripService } from '../../../../core/services/trip.service';

@Component({
  selector: 'app-documents-generated',
  templateUrl: './documents-generated.component.html',
  styleUrls: ['./documents-generated.component.css'],
  standalone: false
})
export class DocumentsGeneratedComponent implements OnInit {
  trips: Trip[] = [];
  total = 0;
  currentPage = 1;
  limit = 5;
  searchTerm = '';
  isLoading = false;
  userRole = 'operator';

  isDocumentsModalOpen = false;
  selectedTripId = '';

  constructor(
    private authService: AuthService,
    private tripService: TripService,
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

    this.tripService.getTrips(this.currentPage, this.limit, this.searchTerm, 'todos').subscribe({
      next: (result) => {
        this.trips = result.items;
        this.total = result.total;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando documentos generados:', error);
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

  openDocumentsModal(tripId: string): void {
    this.selectedTripId = tripId;
    this.isDocumentsModalOpen = true;
  }

  closeDocumentsModal(): void {
    this.isDocumentsModalOpen = false;
    this.selectedTripId = '';
  }

  onDocumentsReconciled(): void {
    this.closeDocumentsModal();
    this.loadTrips();
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

  getDocumentsCount(trip: Trip): number {
    return Number(!!trip.documentos?.ordenCargueUrl) + Number(!!trip.documentos?.manifiestoUrl) + Number(!!trip.documentos?.cumplidoUrl);
  }

  getDocumentsBadgeClass(trip: Trip): string {
    const count = this.getDocumentsCount(trip);
    if (count === 3) {
      return 'bg-green-500 text-white';
    }
    if (count === 0) {
      return 'bg-red-500 text-white';
    }
    return 'bg-orange-500 text-white';
  }
}
