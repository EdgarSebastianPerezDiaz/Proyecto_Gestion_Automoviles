import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Trip, TripService } from '../../../core/services/trip.service';
import { Fulfillment, FulfillmentService } from '../../../core/services/fulfillment.service';

@Component({
  selector: 'app-fulfillment-form-modal',
  templateUrl: './fulfillment-form-modal.component.html',
  styleUrls: ['./fulfillment-form-modal.component.css'],
  standalone: false
})
export class FulfillmentFormModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() tripId = '';

  @Output() saved = new EventEmitter<Fulfillment>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted = false;
  loadingTrips = false;
  availableTrips: Trip[] = [];

  constructor(
    private fb: FormBuilder,
    private tripService: TripService,
    private fulfillmentService: FulfillmentService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.initializeForm();
    this.loadTrips();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['isOpen'] || changes['tripId']) {
      this.resetFormState();
      this.loadTrips();
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      tripId: ['', [Validators.required]],
      fechaEntrega: ['', [Validators.required]],
      horaEntrega: ['', [Validators.required]],
      recibidoPor: ['', [Validators.required, Validators.minLength(3)]],
      observaciones: ['']
    });
  }

  private resetFormState(): void {
    if (!this.form) {
      return;
    }

    this.form.reset({
      tripId: this.tripId || '',
      fechaEntrega: '',
      horaEntrega: '',
      recibidoPor: '',
      observaciones: ''
    }, { emitEvent: false });
    this.submitted = false;
    this.cdr.markForCheck();
  }

  private loadTrips(): void {
    this.loadingTrips = true;
    this.tripService.getDeliveredTripsWithoutFulfillment().subscribe({
      next: (trips) => {
        this.availableTrips = trips;
        if (this.form) {
          this.form.patchValue({ tripId: this.tripId || this.form.get('tripId')?.value || '' }, { emitEvent: false });
        }
        this.loadingTrips = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando viajes para cumplidos:', error);
        this.loadingTrips = false;
        this.cdr.markForCheck();
      }
    });
  }

  private toDateInputValue(date: Date | string): string {
    const dateValue = new Date(date);
    const year = dateValue.getFullYear();
    const month = String(dateValue.getMonth() + 1).padStart(2, '0');
    const day = String(dateValue.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  onSubmit(): void {
    this.submitted = true;
    this.form.markAllAsTouched();

    if (this.form.invalid) {
      return;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const fechaEntrega = new Date(this.form.value.fechaEntrega);
    if (fechaEntrega > today) {
      const control = this.form.get('fechaEntrega');
      control?.setErrors({ ...(control.errors || {}), futureDate: true });
      return;
    }

    const selectedTrip = this.availableTrips.find(trip => trip.id === this.form.value.tripId);
    if (!selectedTrip) {
      return;
    }

    const fulfillmentPayload = {
      tripId: selectedTrip.id,
      tripNombre: `${selectedTrip.origenNombre || selectedTrip.origin} → ${selectedTrip.destinoNombre || selectedTrip.destination}`,
      fechaEntrega: fechaEntrega,
      horaEntrega: this.form.value.horaEntrega,
      recibidoPor: this.form.value.recibidoPor,
      observaciones: this.form.value.observaciones || undefined,
      estadoPago: 'Pendiente' as const
    };

    this.fulfillmentService.createFulfillment(fulfillmentPayload).subscribe({
      next: (created) => {
        this.saved.emit(created);
        this.closeModal();
      },
      error: (error) => {
        console.error('Error creando cumplido:', error);
      }
    });
  }

  closeModal(): void {
    this.close.emit();
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!control && control.invalid && (control.touched || this.submitted);
  }

  getFieldError(fieldName: string): string {
    const control = this.form.get(fieldName);
    if (!control || (!control.touched && !this.submitted) || !control.errors) {
      return '';
    }

    if (control.errors['required']) {
      return 'Campo obligatorio';
    }

    if (control.errors['minlength']) {
      return 'Debe tener al menos 3 caracteres';
    }

    if (control.errors['futureDate']) {
      return 'La fecha de entrega no puede ser futura';
    }

    return 'Campo inválido';
  }
}
