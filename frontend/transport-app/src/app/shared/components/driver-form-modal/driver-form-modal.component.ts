import { Component, Input, Output, EventEmitter, ChangeDetectorRef, OnInit, OnChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Driver } from '../../../core/services/driver.service';

@Component({
  selector: 'app-driver-form-modal',
  templateUrl: './driver-form-modal.component.html',
  styleUrls: ['./driver-form-modal.component.scss'],
  standalone: false
})
export class DriverFormModalComponent implements OnInit, OnChanges {

  @Input() isOpen: boolean = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() driverData: Driver | null = null;
  @Output() saved = new EventEmitter<any>();
  @Output() close = new EventEmitter<void>();

  form: FormGroup;
  cedulasUsed: string[] = ['12.345.678', '98.765.432', '55.111.222']; // Cédulas existentes

  constructor(private fb: FormBuilder, private cdr: ChangeDetectorRef) {
    this.form = this.fb.group({
      fullName: ['', [Validators.required, Validators.minLength(5)]],
      cedula: ['', [Validators.required, this.cedulaValidator.bind(this)]],
      telefono: ['', [Validators.required, Validators.pattern(/^[+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4,6}$/)]],
      direccion: ['', [Validators.required, Validators.minLength(5)]],
      correo: ['', [Validators.required, Validators.email]],
      numeroLicencia: ['', Validators.required],
      categoriaLicencia: ['C3', Validators.required],
      fechaVencimientoLicencia: ['', [Validators.required, this.futureDateValidator.bind(this)]]
    });
  }

  ngOnInit() {
    this.updateForm();
  }

  ngOnChanges() {
    this.updateForm();
  }

  /**
   * Actualizar formulario con datos del conductor en modo edición
   */
  updateForm() {
    if (this.mode === 'edit' && this.driverData) {
      this.form.patchValue({
        fullName: this.driverData.fullName,
        cedula: this.driverData.cedula,
        telefono: this.driverData.telefono,
        direccion: this.driverData.direccion,
        correo: this.driverData.correo,
        numeroLicencia: this.driverData.numeroLicencia,
        categoriaLicencia: this.driverData.categoriaLicencia,
        fechaVencimientoLicencia: this.driverData.fechaVencimientoLicencia
      });
      // En modo edición, permitir la cédula actual
      if (this.driverData.cedula) {
        this.cedulasUsed = this.cedulasUsed.filter(c => c !== this.driverData!.cedula);
      }
    } else {
      this.form.reset({ categoriaLicencia: 'C3' });
    }
    this.cdr.markForCheck();
  }

  /**
   * Validador personalizado para cédula única
   */
  cedulaValidator(control: any) {
    if (!control.value) {
      return null;
    }
    if (this.cedulasUsed.includes(control.value)) {
      return { cedulaExists: true };
    }
    return null;
  }

  /**
   * Validador para fecha no pasada
   */
  futureDateValidator(control: any) {
    if (!control.value) {
      return null;
    }
    const selectedDate = new Date(control.value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (selectedDate < today) {
      return { pastDate: true };
    }
    return null;
  }

  /**
   * Obtener mensaje de error para campo específico
   */
  getFieldError(fieldName: string): string {
    const control = this.form.get(fieldName);
    if (!control || !control.errors || !control.touched) {
      return '';
    }

    if (control.errors['required']) return `${this.getFieldLabel(fieldName)} es requerido`;
    if (control.errors['minlength']) return `Mínimo ${control.errors['minlength'].requiredLength} caracteres`;
    if (control.errors['email']) return 'Correo inválido';
    if (control.errors['pattern']) return `Formato inválido de ${this.getFieldLabel(fieldName).toLowerCase()}`;
    if (control.errors['cedulaExists']) return 'Esta cédula ya está registrada';
    if (control.errors['pastDate']) return 'La fecha no puede ser pasada';

    return 'Error en este campo';
  }

  /**
   * Obtener etiqueta de campo
   */
  getFieldLabel(fieldName: string): string {
    const labels: any = {
      fullName: 'Nombre Completo',
      cedula: 'Cédula',
      telefono: 'Teléfono',
      direccion: 'Dirección',
      correo: 'Correo Electrónico',
      numeroLicencia: 'N° Licencia',
      categoriaLicencia: 'Categoría de Licencia',
      fechaVencimientoLicencia: 'Fecha Vencimiento Licencia'
    };
    return labels[fieldName] || fieldName;
  }

  /**
   * Enviar formulario
   */
  onSubmit() {
    if (this.form.valid) {
      this.saved.emit(this.form.value);
    }
  }

  /**
   * Cerrar modal
   */
  closeModal() {
    this.close.emit();
  }
}
