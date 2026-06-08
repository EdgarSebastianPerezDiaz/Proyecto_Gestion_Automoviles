import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CargoType } from '../../../core/services/cargo-type.service';

@Component({
  selector: 'app-cargo-type-form-modal',
  templateUrl: './cargo-type-form-modal.component.html',
  styleUrls: ['./cargo-type-form-modal.component.css'],
  standalone: false
})
export class CargoTypeFormModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() cargoType: CargoType | null = null;

  @Output() saved = new EventEmitter<CargoType>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted = false;

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initializeForm();
    this.syncFormWithCargoType();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['cargoType'] || changes['mode'] || changes['isOpen']) {
      this.syncFormWithCargoType();
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      descripcion: ['', [Validators.required, Validators.minLength(5)]],
      pesoReferencia: ['', [Validators.min(0.01)]],
      precioPorTon: ['', [Validators.required, Validators.min(0.01)]]
    });
  }

  private syncFormWithCargoType(): void {
    if (!this.form) {
      return;
    }

    if (this.mode === 'edit' && this.cargoType) {
      this.form.patchValue({
        nombre: this.cargoType.nombre,
        descripcion: this.cargoType.descripcion,
        pesoReferencia: this.cargoType.pesoReferencia ?? '',
        precioPorTon: this.cargoType.precioPorTon
      });
    } else {
      this.form.reset({
        nombre: '',
        descripcion: '',
        pesoReferencia: '',
        precioPorTon: ''
      });
    }

    this.submitted = false;
  }

  onSubmit(): void {
    this.submitted = true;
    this.form.markAllAsTouched();

    if (this.form.invalid) {
      return;
    }

    const formValue = this.form.value;
    const payload: CargoType = {
      id: this.cargoType?.id || '',
      nombre: formValue.nombre,
      descripcion: formValue.descripcion,
      pesoReferencia: formValue.pesoReferencia !== '' && formValue.pesoReferencia !== null ? Number(formValue.pesoReferencia) : undefined,
      precioPorTon: Number(formValue.precioPorTon)
    };

    this.saved.emit(payload);
    this.closeModal();
  }

  closeModal(): void {
    this.submitted = false;
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
      return `${this.getFieldLabel(fieldName)} debe tener al menos ${control.errors['minlength'].requiredLength} caracteres`;
    }

    if (control.errors['min']) {
      return `${this.getFieldLabel(fieldName)} debe ser mayor que 0`;
    }

    return 'Campo inválido';
  }

  getFieldLabel(fieldName: string): string {
    const labels: Record<string, string> = {
      nombre: 'Tipo de Carga',
      descripcion: 'Descripción',
      pesoReferencia: 'Peso de Referencia',
      precioPorTon: 'Precio por Tonelada'
    };

    return labels[fieldName] || fieldName;
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!control && control.invalid && (control.touched || this.submitted);
  }
}
