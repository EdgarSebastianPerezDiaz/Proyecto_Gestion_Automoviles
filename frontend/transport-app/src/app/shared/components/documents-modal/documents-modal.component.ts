import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { Trip, TripService } from '../../../core/services/trip.service';

@Component({
  selector: 'app-documents-modal',
  templateUrl: './documents-modal.component.html',
  styleUrls: ['./documents-modal.component.css'],
  standalone: false
})
export class DocumentsModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() tripId = '';

  @Output() close = new EventEmitter<void>();
  @Output() reconciled = new EventEmitter<string>();

  trip: Trip | null = null;
  loading = false;
  reconciling = false;

  constructor(private tripService: TripService) {}

  ngOnInit(): void {
    this.loadTrip();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['tripId'] || changes['isOpen']) {
      this.loadTrip();
    }
  }

  loadTrip(): void {
    if (!this.isOpen || !this.tripId) {
      return;
    }

    this.loading = true;
    this.tripService.getTripById(this.tripId).subscribe({
      next: (trip) => {
        this.trip = trip || null;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error cargando documentos del viaje:', error);
        this.loading = false;
      }
    });
  }

  hasMissingDocuments(): boolean {
    if (!this.trip) {
      return false;
    }

    return !this.trip.documentos?.ordenCargueUrl || !this.trip.documentos?.manifiestoUrl || !this.trip.documentos?.cumplidoUrl;
  }

  reconcile(): void {
    if (!this.tripId) {
      return;
    }

    this.reconciling = true;
    this.tripService.reconcileDocuments(this.tripId).subscribe({
      next: (trip) => {
        this.trip = trip;
        this.reconciling = false;
        this.reconciled.emit(this.tripId);
      },
      error: (error) => {
        console.error('Error reconciliando documentos:', error);
        this.reconciling = false;
      }
    });
  }

  closeModal(): void {
    this.close.emit();
  }
}
