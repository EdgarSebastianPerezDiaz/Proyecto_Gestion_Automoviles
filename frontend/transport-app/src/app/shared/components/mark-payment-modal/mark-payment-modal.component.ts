import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Fulfillment, FulfillmentService } from '../../../core/services/fulfillment.service';

@Component({
  selector: 'app-mark-payment-modal',
  templateUrl: './mark-payment-modal.component.html',
  styleUrls: ['./mark-payment-modal.component.css'],
  standalone: false
})
export class MarkPaymentModalComponent {
  @Input() isOpen = false;
  @Input() fulfillment: Fulfillment | null = null;

  @Output() confirmed = new EventEmitter<Fulfillment>();
  @Output() saved = new EventEmitter<Fulfillment>();
  @Output() close = new EventEmitter<void>();

  constructor(private fulfillmentService: FulfillmentService) {}

  confirm(): void {
    if (!this.fulfillment) {
      return;
    }

    this.fulfillmentService.markAsPaid(this.fulfillment.id).subscribe({
      next: (updated) => {
        this.confirmed.emit(updated);
        this.saved.emit(updated);
        this.close.emit();
      },
      error: (error) => {
        console.error('Error marcando cumplido como pagado:', error);
      }
    });
  }

  closeModal(): void {
    this.close.emit();
  }
}
