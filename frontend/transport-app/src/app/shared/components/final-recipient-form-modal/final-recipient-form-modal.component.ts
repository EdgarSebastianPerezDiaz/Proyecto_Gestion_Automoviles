import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { FinalRecipient } from '../../../core/services/final-recipient.service';

@Component({
  selector: 'app-final-recipient-form-modal',
  templateUrl: './final-recipient-form-modal.component.html',
  styleUrls: ['./final-recipient-form-modal.component.css'],
  standalone: false
})
export class FinalRecipientFormModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() finalRecipient: FinalRecipient | null = null;

  @Output() saved = new EventEmitter<FinalRecipient>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted = false;

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initializeForm();
    this.syncFormWithRecipient();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['finalRecipient'] || changes['mode'] || changes['isOpen']) {
      this.syncFormWithRecipient();
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      nit: ['', [Validators.required, Validators.pattern(/^[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]$/)]],
      direccion: ['', [Validators.required]],
      telefono: ['', [Validators.required]],
      correo: ['', [Validators.required, Validators.email]]
    });
  }

  private syncFormWithRecipient(): void {
    if (!this.form) {
      return;
    }

    if (this.mode === 'edit' && this.finalRecipient) {
      this.form.patchValue({
        nombre: this.finalRecipient.nombre,
        nit: this.finalRecipient.nit,
        direccion: this.finalRecipient.direccion,
        telefono: this.finalRecipient.telefono,
        correo: this.finalRecipient.correo
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

    const payload: FinalRecipient = {
      id: this.finalRecipient?.id || '',
      ...this.form.value
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

    if (control.errors['pattern']) {
      return `${this.getFieldLabel(fieldName)} tiene un formato inválido`;
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
      correo: 'Correo'
    };

    return labels[fieldName] || fieldName;
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!control && control.invalid && (control.touched || this.submitted);
  }
}
