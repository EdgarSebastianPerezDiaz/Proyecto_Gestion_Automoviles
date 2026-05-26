import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Transportista } from '../../../core/services/transportista.service';

@Component({
  selector: 'app-transportista-form-modal',
  templateUrl: './transportista-form-modal.component.html',
  styleUrls: ['./transportista-form-modal.component.css'],
  standalone: false
})
export class TransportistaFormModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() transportista: Transportista | null = null;

  @Output() saved = new EventEmitter<Transportista>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted = false;

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initializeForm();
    this.syncFormWithTransportista();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['transportista'] || changes['mode'] || changes['isOpen']) {
      this.syncFormWithTransportista();
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      nit: ['', [Validators.required]],
      direccion: ['', [Validators.required]],
      telefono: ['', [Validators.required]],
      correo: ['', [Validators.required, Validators.email]],
      tipoDocumento: ['']
    });
  }

  private syncFormWithTransportista(): void {
    if (!this.form) {
      return;
    }

    if (this.mode === 'edit' && this.transportista) {
      this.form.patchValue({
        nombre: this.transportista.nombre,
        nit: this.transportista.nit,
        direccion: this.transportista.direccion,
        telefono: this.transportista.telefono,
        correo: this.transportista.correo,
        tipoDocumento: this.transportista.tipoDocumento || ''
      });
    } else {
      this.form.reset();
    }

    this.submitted = false;
  }

  onSubmit(): void {
    this.submitted = true;
    this.form.markAllAsTouched();

    if (this.form.invalid) {
      return;
    }

    const payload: Transportista = {
      id: this.transportista?.id || '',
      nombre: this.form.value.nombre,
      nit: this.form.value.nit,
      direccion: this.form.value.direccion,
      telefono: this.form.value.telefono,
      correo: this.form.value.correo,
      tipoDocumento: this.form.value.tipoDocumento || undefined
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
      return `${this.getFieldLabel(fieldName)} debe tener al menos 3 caracteres`;
    }

    if (control.errors['email']) {
      return 'El correo electrónico no es válido';
    }

    return 'Campo inválido';
  }

  getFieldLabel(fieldName: string): string {
    const labels: Record<string, string> = {
      nombre: 'Nombre',
      nit: 'NIT',
      direccion: 'Dirección',
      telefono: 'Teléfono',
      correo: 'Correo',
      tipoDocumento: 'Tipo de Documento'
    };

    return labels[fieldName] || fieldName;
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!control && control.invalid && (control.touched || this.submitted);
  }
}
