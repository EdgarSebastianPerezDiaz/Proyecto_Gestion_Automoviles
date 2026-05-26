import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { Driver, DriverService } from '../../../core/services/driver.service';
import { Transportista, TransportistaService } from '../../../core/services/transportista.service';
import { Vehicle, VehicleService } from '../../../core/services/vehicle.service';

@Component({
  selector: 'app-vehicle-form-modal',
  templateUrl: './vehicle-form-modal.component.html',
  styleUrls: ['./vehicle-form-modal.component.css'],
  standalone: false
})
export class VehicleFormModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() vehicle: Vehicle | null = null;

  @Output() saved = new EventEmitter<Vehicle>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted = false;
  transportistas: Transportista[] = [];
  drivers: Driver[] = [];
  loadingOptions = false;

  constructor(
    private fb: FormBuilder,
    private transportistaService: TransportistaService,
    private driverService: DriverService,
    private vehicleService: VehicleService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.initializeForm();
    this.loadDropdownData();
    this.syncFormWithVehicle();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['vehicle'] || changes['mode'] || changes['isOpen']) {
      this.syncFormWithVehicle();
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      placa: ['', [Validators.required, Validators.pattern(/^[A-Z0-9-]+$/)]],
      marca: ['', [Validators.required, Validators.minLength(2)]],
      modelo: ['', [Validators.required, Validators.minLength(1)]],
      capacidad: ['', [Validators.required, Validators.min(0.01)]],
      estado: ['Disponible', [Validators.required]],
      transportistaId: ['', [Validators.required]],
      conductorId: ['']
    });
  }

  private loadDropdownData(): void {
    this.loadingOptions = true;
    forkJoin({
      transportistas: this.transportistaService.getAll(),
      drivers: this.driverService.getDrivers(1, 1000, '')
    }).subscribe({
      next: ({ transportistas, drivers }) => {
        this.transportistas = transportistas;
        this.drivers = drivers.items;
        this.loadingOptions = false;
        this.syncFormWithVehicle();
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando opciones del formulario de vehículos:', error);
        this.loadingOptions = false;
        this.cdr.markForCheck();
      }
    });
  }

  private syncFormWithVehicle(): void {
    if (!this.form) {
      return;
    }

    if (this.mode === 'edit' && this.vehicle) {
      this.form.patchValue({
        placa: this.vehicle.placa,
        marca: this.vehicle.marca,
        modelo: this.vehicle.modelo,
        capacidad: this.vehicle.capacidad,
        estado: this.vehicle.estado,
        transportistaId: this.vehicle.transportistaId,
        conductorId: this.vehicle.conductorId || ''
      });
    } else {
      this.form.reset({
        placa: '',
        marca: '',
        modelo: '',
        capacidad: '',
        estado: 'Disponible',
        transportistaId: '',
        conductorId: ''
      });
    }

    this.submitted = false;
    this.clearPlateExistsError();
    this.cdr.markForCheck();
  }

  private clearPlateExistsError(): void {
    const control = this.form.get('placa');
    if (!control?.errors?.['plateExists']) {
      return;
    }

    const errors = { ...control.errors };
    delete errors['plateExists'];
    control.setErrors(Object.keys(errors).length > 0 ? errors : null);
  }

  onSubmit(): void {
    this.submitted = true;
    this.form.markAllAsTouched();

    if (this.form.invalid) {
      return;
    }

    const formValue = this.form.value;
    const payload: Vehicle = {
      id: this.vehicle?.id || '',
      placa: String(formValue.placa || '').toUpperCase(),
      marca: formValue.marca,
      modelo: formValue.modelo,
      capacidad: Number(formValue.capacidad),
      estado: formValue.estado,
      transportistaId: formValue.transportistaId,
      conductorId: formValue.conductorId || undefined
    };

    this.vehicleService.getVehicles(1, 1000, '').subscribe({
      next: (result) => {
        const duplicate = result.items.some(vehicle =>
          vehicle.placa.toUpperCase() === payload.placa.toUpperCase() && vehicle.id !== payload.id
        );

        if (duplicate) {
          const control = this.form.get('placa');
          control?.setErrors({ ...(control.errors || {}), plateExists: true });
          return;
        }

        this.clearPlateExistsError();
        this.saved.emit(payload);
        this.closeModal();
      },
      error: (error) => {
        console.error('Error validando placa duplicada:', error);
      }
    });
  }

  closeModal(): void {
    this.submitted = false;
    this.clearPlateExistsError();
    this.close.emit();
  }

  getFieldError(fieldName: string): string {
    const control = this.form.get(fieldName);
    if (!control || (!control.touched && !this.submitted) || !control.errors) {
      return '';
    }

    if (control.errors['required']) {
      return `${this.getFieldLabel(fieldName)} es obligatorio`;
    }

    if (control.errors['minlength']) {
      return `${this.getFieldLabel(fieldName)} debe tener más caracteres`;
    }

    if (control.errors['pattern']) {
      return `${this.getFieldLabel(fieldName)} tiene un formato inválido`;
    }

    if (control.errors['min']) {
      return 'La capacidad debe ser mayor que 0';
    }

    if (control.errors['plateExists']) {
      return 'La placa ya existe en otro vehículo';
    }

    return 'Campo inválido';
  }

  getFieldLabel(fieldName: string): string {
    const labels: Record<string, string> = {
      placa: 'Placa',
      marca: 'Marca',
      modelo: 'Modelo',
      capacidad: 'Capacidad',
      estado: 'Estado',
      transportistaId: 'Transportista',
      conductorId: 'Conductor'
    };

    return labels[fieldName] || fieldName;
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!control && (control.invalid && (control.touched || this.submitted));
  }
}
