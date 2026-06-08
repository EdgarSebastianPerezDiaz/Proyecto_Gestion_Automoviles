import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { TripStatus } from '../../../core/services/trip.service';

@Component({
  selector: 'app-change-status-modal',
  templateUrl: './change-status-modal.component.html',
  styleUrls: ['./change-status-modal.component.css'],
  standalone: false
})
export class ChangeStatusModalComponent implements OnChanges {
  @Input() isOpen = false;
  @Input() currentStatus: TripStatus = 'Programado';

  @Output() statusChanged = new EventEmitter<TripStatus>();
  @Output() close = new EventEmitter<void>();

  selectedStatus: TripStatus | '' = '';

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['currentStatus'] || changes['isOpen']) {
      const options = this.getAllowedStatuses();
      this.selectedStatus = options.length > 0 ? options[0] : '';
    }
  }

  getAllowedStatuses(): TripStatus[] {
    switch (this.currentStatus) {
      case 'Programado':
        return ['En Ruta', 'Cancelado'];
      case 'En Ruta':
        return ['Entregado', 'Cancelado'];
      default:
        return [];
    }
  }

  confirm(): void {
    if (!this.selectedStatus) {
      return;
    }

    this.statusChanged.emit(this.selectedStatus);
    this.close.emit();
  }

  closeModal(): void {
    this.close.emit();
  }
}
