import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Fulfillment } from '../../../core/services/fulfillment.service';

@Component({
  selector: 'app-fulfillment-details-modal',
  templateUrl: './fulfillment-details-modal.component.html',
  styleUrls: ['./fulfillment-details-modal.component.css'],
  standalone: false
})
export class FulfillmentDetailsModalComponent {
  @Input() isOpen = false;
  @Input() fulfillment: Fulfillment | null = null;

  @Output() close = new EventEmitter<void>();

  closeModal(): void {
    this.close.emit();
  }
}
