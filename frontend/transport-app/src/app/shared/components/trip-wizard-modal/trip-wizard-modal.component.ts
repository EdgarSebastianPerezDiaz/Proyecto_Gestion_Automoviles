import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { Company, CompanyService } from '../../../core/services/company.service';
import { CargoType, CargoTypeService } from '../../../core/services/cargo-type.service';
import { Driver, DriverService } from '../../../core/services/driver.service';
import { FinalRecipient, FinalRecipientService } from '../../../core/services/final-recipient.service';
import { Trip, TripService } from '../../../core/services/trip.service';
import { Transportista, TransportistaService } from '../../../core/services/transportista.service';
import { Vehicle, VehicleService } from '../../../core/services/vehicle.service';

@Component({
  selector: 'app-trip-wizard-modal',
  templateUrl: './trip-wizard-modal.component.html',
  styleUrls: ['./trip-wizard-modal.component.css'],
  standalone: false
})
export class TripWizardModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() trip: Trip | null = null;

  @Output() saved = new EventEmitter<Trip>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted = false;
  currentStep = 1;
  loadingOptions = false;
  dateMin = new Date().toISOString().split('T')[0];

  companies: Company[] = [];
  finalRecipients: FinalRecipient[] = [];
  transportistas: Transportista[] = [];
  allVehicles: Vehicle[] = [];
  allDrivers: Driver[] = [];
  cargoTypes: CargoType[] = [];

  filteredVehicles: Vehicle[] = [];
  filteredDrivers: Driver[] = [];
  selectedVehicle: Vehicle | null = null;
  selectedCargoType: CargoType | null = null;
  costoTotal = 0;

  constructor(
    private fb: FormBuilder,
    private companyService: CompanyService,
    private finalRecipientService: FinalRecipientService,
    private transportistaService: TransportistaService,
    private driverService: DriverService,
    private vehicleService: VehicleService,
    private cargoTypeService: CargoTypeService,
    private tripService: TripService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.initializeForm();
    this.loadDropdownData();
    this.syncFormWithTrip();
    this.bindFormListeners();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['trip'] || changes['mode'] || changes['isOpen']) {
      this.syncFormWithTrip();
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      origenId: ['', [Validators.required]],
      destinoId: ['', [Validators.required]],
      fechaSalida: ['', [Validators.required]],
      fechaLlegadaEstimada: ['', [Validators.required]],
      transportistaId: ['', [Validators.required]],
      vehiculoId: ['', [Validators.required]],
      conductorId: ['', [Validators.required]],
      cargoTypeId: ['', [Validators.required]],
      peso: ['', [Validators.required, Validators.min(0.01)]],
      precioPorTon: ['', [Validators.required, Validators.min(0.01)]],
      costoTotal: [{ value: 0, disabled: true }]
    });
  }

  private bindFormListeners(): void {
    this.form.get('transportistaId')?.valueChanges.subscribe((transportistaId) => {
      this.applyTransportistaFilters(transportistaId);
      this.form.patchValue({ vehiculoId: '', conductorId: '' }, { emitEvent: false });
      this.selectedVehicle = null;
      this.updateWeightValidation();
      this.cdr.markForCheck();
    });

    this.form.get('vehiculoId')?.valueChanges.subscribe((vehiculoId) => {
      this.selectedVehicle = this.filteredVehicles.find(vehicle => vehicle.id === vehiculoId) || null;
      this.updateWeightValidation();
      this.cdr.markForCheck();
    });

    this.form.get('cargoTypeId')?.valueChanges.subscribe((cargoTypeId) => {
      this.selectedCargoType = this.cargoTypes.find(cargoType => cargoType.id === cargoTypeId) || null;
      this.updateCost();
      this.cdr.markForCheck();
    });

    this.form.get('peso')?.valueChanges.subscribe(() => {
      this.updateWeightValidation();
      this.updateCost();
      this.cdr.markForCheck();
    });
  }

  private loadDropdownData(): void {
    this.loadingOptions = true;
    forkJoin({
      companies: this.companyService.getCompanies(1, 1000, ''),
      finalRecipients: this.finalRecipientService.getAll(),
      transportistas: this.transportistaService.getAll(),
      vehicles: this.vehicleService.getVehicles(1, 1000, '', 'todos'),
      drivers: this.driverService.getDrivers(1, 1000, ''),
      cargoTypes: this.cargoTypeService.getCargoTypes(1, 1000, '')
    }).subscribe({
      next: ({ companies, finalRecipients, transportistas, vehicles, drivers, cargoTypes }) => {
        this.companies = companies.items;
        this.finalRecipients = finalRecipients;
        this.transportistas = transportistas;
        this.allVehicles = vehicles.items;
        this.allDrivers = drivers.items;
        this.cargoTypes = cargoTypes.items;
        this.loadingOptions = false;
        this.applyTransportistaFilters(this.form.get('transportistaId')?.value || '');
        this.syncFormWithTrip();
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error cargando datos del wizard de viajes:', error);
        this.loadingOptions = false;
        this.cdr.markForCheck();
      }
    });
  }

  private syncFormWithTrip(): void {
    if (!this.form) {
      return;
    }

    if (this.mode === 'edit' && this.trip) {
      this.form.patchValue({
        origenId: this.trip.origenId,
        destinoId: this.trip.destinoId,
        fechaSalida: this.toDateInputValue(this.trip.fechaSalida),
        fechaLlegadaEstimada: this.toDateInputValue(this.trip.fechaLlegadaEstimada),
        transportistaId: this.trip.transportistaId,
        vehiculoId: this.trip.vehiculoId,
        conductorId: this.trip.conductorId,
        cargoTypeId: this.trip.cargoTypeId,
        peso: this.trip.peso,
        precioPorTon: this.trip.precioPorTon || 0,
        costoTotal: this.trip.costoTotal
      }, { emitEvent: false });

      this.selectedVehicle = this.allVehicles.find(vehicle => vehicle.id === this.trip?.vehiculoId) || null;
      this.selectedCargoType = this.cargoTypes.find(cargoType => cargoType.id === this.trip?.cargoTypeId) || null;
      this.applyTransportistaFilters(this.trip.transportistaId);
      this.updateCost();
    } else {
      this.form.reset({
        origenId: '',
        destinoId: '',
        fechaSalida: '',
        fechaLlegadaEstimada: '',
        transportistaId: '',
        vehiculoId: '',
        conductorId: '',
        cargoTypeId: '',
        peso: '',
        precioPorTon: '',
        costoTotal: 0
      }, { emitEvent: false });
      this.selectedVehicle = null;
      this.selectedCargoType = null;
      this.filteredVehicles = [];
      this.filteredDrivers = [];
      this.costoTotal = 0;
    }

    this.submitted = false;
    this.currentStep = 1;
    this.clearFormErrors();
    this.cdr.markForCheck();
  }

  private toDateInputValue(dateValue: Date | string): string {
    const date = new Date(dateValue);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private applyTransportistaFilters(transportistaId: string): void {
    this.filteredVehicles = this.allVehicles.filter(vehicle =>
      vehicle.transportistaId === transportistaId && vehicle.estado === 'Disponible'
    );

    this.filteredDrivers = this.allDrivers.filter(driver =>
      driver.transportistaId === transportistaId && this.isLicenseValid(driver.fechaVencimientoLicencia)
    );

    const currentVehicleId = this.form.get('vehiculoId')?.value;
    if (currentVehicleId && !this.filteredVehicles.some(vehicle => vehicle.id === currentVehicleId)) {
      this.form.patchValue({ vehiculoId: '' }, { emitEvent: false });
      this.selectedVehicle = null;
    }

    const currentDriverId = this.form.get('conductorId')?.value;
    if (currentDriverId && !this.filteredDrivers.some(driver => driver.id === currentDriverId)) {
      this.form.patchValue({ conductorId: '' }, { emitEvent: false });
    }
  }

  private isLicenseValid(fechaVencimiento: string): boolean {
    const expiryDate = new Date(fechaVencimiento);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return expiryDate >= today;
  }

  private updateWeightValidation(): void {
    const pesoControl = this.form.get('peso');
    if (!pesoControl) {
      return;
    }

    const pesoValue = Number(pesoControl.value || 0);
    const capacity = this.selectedVehicle?.capacidad || 0;
    const errors = { ...(pesoControl.errors || {}) };

    if (this.selectedVehicle && pesoValue > capacity) {
      errors['maxCapacity'] = true;
    } else {
      delete errors['maxCapacity'];
    }

    pesoControl.setErrors(Object.keys(errors).length > 0 ? errors : null);
  }

  private updateCost(): void {
    const peso = Number(this.form.get('peso')?.value || 0);
    const precioPorTon = this.selectedCargoType?.precioPorTon || Number(this.form.get('precioPorTon')?.value || 0);
    const costo = peso > 0 && precioPorTon > 0 ? peso * precioPorTon : 0;
    this.costoTotal = costo;
    this.form.patchValue({ precioPorTon, costoTotal: costo }, { emitEvent: false });
  }

  nextStep(): void {
    if (!this.isCurrentStepValid()) {
      this.markCurrentStepTouched();
      return;
    }

    if (this.currentStep < 3) {
      this.currentStep++;
    }
  }

  previousStep(): void {
    if (this.currentStep > 1) {
      this.currentStep--;
    }
  }

  private markCurrentStepTouched(): void {
    this.getStepControlNames(this.currentStep).forEach(controlName => {
      this.form.get(controlName)?.markAsTouched();
    });
    this.updateDatesValidation();
    this.updateWeightValidation();
  }

  private getStepControlNames(step: number): string[] {
    switch (step) {
      case 1:
        return ['origenId', 'destinoId', 'fechaSalida', 'fechaLlegadaEstimada'];
      case 2:
        return ['transportistaId', 'vehiculoId', 'conductorId'];
      case 3:
      default:
        return ['cargoTypeId', 'peso'];
    }
  }

  private isCurrentStepValid(): boolean {
    this.updateDatesValidation();
    this.updateWeightValidation();
    return this.getStepControlNames(this.currentStep).every(controlName => this.form.get(controlName)?.valid);
  }

  private updateDatesValidation(): void {
    const fechaSalidaControl = this.form.get('fechaSalida');
    const fechaLlegadaControl = this.form.get('fechaLlegadaEstimada');

    if (!fechaSalidaControl || !fechaLlegadaControl) {
      return;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const salida = fechaSalidaControl.value ? new Date(fechaSalidaControl.value) : null;
    const llegada = fechaLlegadaControl.value ? new Date(fechaLlegadaControl.value) : null;

    const salidaErrors = { ...(fechaSalidaControl.errors || {}) };
    const llegadaErrors = { ...(fechaLlegadaControl.errors || {}) };

    if (salida && salida < today) {
      salidaErrors['pastDate'] = true;
    } else {
      delete salidaErrors['pastDate'];
    }

    if (salida && llegada && llegada <= salida) {
      llegadaErrors['invalidRange'] = true;
    } else {
      delete llegadaErrors['invalidRange'];
    }

    fechaSalidaControl.setErrors(Object.keys(salidaErrors).length > 0 ? salidaErrors : null);
    fechaLlegadaControl.setErrors(Object.keys(llegadaErrors).length > 0 ? llegadaErrors : null);
  }

  onSubmit(): void {
    this.submitted = true;
    this.updateDatesValidation();
    this.updateWeightValidation();
    this.form.markAllAsTouched();

    if (this.form.invalid || this.currentStep !== 3) {
      return;
    }

    const selectedOrigin = this.companies.find(company => company.id === this.form.value.origenId);
    const selectedDestination = this.finalRecipients.find(recipient => recipient.id === this.form.value.destinoId);
    const selectedTransportista = this.transportistas.find(item => item.id === this.form.value.transportistaId);
    const selectedVehicle = this.filteredVehicles.find(vehicle => vehicle.id === this.form.value.vehiculoId) || this.allVehicles.find(vehicle => vehicle.id === this.form.value.vehiculoId);
    const selectedDriver = this.filteredDrivers.find(driver => driver.id === this.form.value.conductorId) || this.allDrivers.find(driver => driver.id === this.form.value.conductorId);
    const selectedCargoType = this.cargoTypes.find(cargoType => cargoType.id === this.form.value.cargoTypeId);

    if (!selectedOrigin || !selectedDestination || !selectedTransportista || !selectedVehicle || !selectedDriver || !selectedCargoType) {
      return;
    }

    const payload: Partial<Trip> = {
      id: this.trip?.id || '',
      origenId: selectedOrigin.id,
      destinoId: selectedDestination.id,
      transportistaId: selectedTransportista.id,
      conductorId: selectedDriver.id,
      vehiculoId: selectedVehicle.id,
      cargoTypeId: selectedCargoType.id,
      peso: Number(this.form.value.peso),
      precioPorTon: selectedCargoType.precioPorTon,
      costoTotal: Number(this.form.value.peso) * selectedCargoType.precioPorTon,
      fechaSalida: new Date(this.form.value.fechaSalida),
      fechaLlegadaEstimada: new Date(this.form.value.fechaLlegadaEstimada),
      estado: this.trip?.estado || 'Programado',
      origenNombre: selectedOrigin.nombre,
      destinoNombre: selectedDestination.nombre,
      transportistaNombre: selectedTransportista.nombre,
      conductorNombre: selectedDriver.fullName,
      vehiculoPlaca: selectedVehicle.placa,
      cargoTypeNombre: selectedCargoType.nombre,
      vehiculoCapacidad: selectedVehicle.capacidad,
      origin: selectedOrigin.nombre,
      destination: selectedDestination.nombre,
      driver: {
        id: selectedDriver.id,
        name: selectedDriver.fullName,
        license: selectedDriver.numeroLicencia
      },
      vehicle: {
        id: selectedVehicle.id,
        plate: selectedVehicle.placa,
        type: `${selectedVehicle.marca} ${selectedVehicle.modelo}`
      },
      startDate: new Date(this.form.value.fechaSalida),
      estimatedEndDate: new Date(this.form.value.fechaLlegadaEstimada),
      cargoWeight: Number(this.form.value.peso),
      cargoType: selectedCargoType.nombre
    };

    const request$ = this.mode === 'create'
      ? this.tripService.createTrip(payload)
      : this.tripService.updateTrip(this.trip!.id, payload as Trip);

    request$.subscribe({
      next: (result) => {
        this.saved.emit(result);
        this.closeModal();
      },
      error: (error) => console.error('Error guardando viaje:', error)
    });
  }

  closeModal(): void {
    this.submitted = false;
    this.close.emit();
  }

  clearFormErrors(): void {
    ['fechaSalida', 'fechaLlegadaEstimada', 'peso'].forEach(controlName => {
      const control = this.form.get(controlName);
      if (control?.errors) {
        control.setErrors(null);
      }
    });
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

    if (control.errors['min']) {
      return `${this.getFieldLabel(fieldName)} debe ser mayor que 0`;
    }

    if (control.errors['pastDate']) {
      return 'La fecha de salida no puede ser pasada';
    }

    if (control.errors['invalidRange']) {
      return 'La fecha de llegada debe ser posterior a la salida';
    }

    if (control.errors['maxCapacity']) {
      return 'El peso supera la capacidad del vehículo seleccionado';
    }

    return 'Campo inválido';
  }

  getFieldLabel(fieldName: string): string {
    const labels: Record<string, string> = {
      origenId: 'Origen',
      destinoId: 'Destino',
      fechaSalida: 'Fecha de Salida',
      fechaLlegadaEstimada: 'Fecha de Llegada Estimada',
      transportistaId: 'Transportista',
      vehiculoId: 'Vehículo',
      conductorId: 'Conductor',
      cargoTypeId: 'Tipo de Carga',
      peso: 'Peso'
    };

    return labels[fieldName] || fieldName;
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!control && control.invalid && (control.touched || this.submitted);
  }

  getSelectedVehicleCapacity(): number {
    return this.selectedVehicle?.capacidad || 0;
  }

  isSaveDisabled(): boolean {
    return this.loadingOptions || !this.form.valid || this.currentStep !== 3;
  }
}
