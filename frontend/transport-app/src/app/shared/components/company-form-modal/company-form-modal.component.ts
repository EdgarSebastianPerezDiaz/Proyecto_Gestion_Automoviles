import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Company } from '../../../core/services/company.service';
import { ModalComponent } from '../modal/modal.component';

@Component({
  selector: 'app-company-form-modal',
  standalone: false,
  templateUrl: './company-form-modal.component.html',
  styleUrls: ['./company-form-modal.component.css']
})
export class CompanyFormModalComponent implements OnInit, OnChanges {
  @Input() isOpen: boolean = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() companyData?: Company;

  @Output() saved = new EventEmitter<Company>();
  @Output() close = new EventEmitter<void>();

  form!: FormGroup;
  submitted: boolean = false;

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['companyData'] && !changes['companyData'].firstChange && this.companyData) {
      this.populateForm(this.companyData);
    }
  }

  private initializeForm(): void {
    this.form = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      nit: ['', [Validators.required, Validators.pattern(/^[0-9]{1,3}\.[0-9]{3}\.[0-9]{3}-?[0-9A-Z]{1}$/)]],
      direccion: ['', [Validators.required]],
      telefono: ['', [Validators.required, Validators.pattern(/^[+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4,6}$/)]],
      correo: ['', [Validators.required, Validators.email]]
    });
  }

  private populateForm(company: Company): void {
    this.form.patchValue({
      nombre: company.nombre,
      nit: company.nit,
      direccion: company.direccion,
      telefono: company.telefono,
      correo: company.correo
    });
  }

  onSubmit(): void {
    this.submitted = true;

    if (this.form.valid) {
      const formValue = this.form.value;
      const company: Company = {
        id: this.companyData?.id || '',
        ...formValue
      };

      this.saved.emit(company);
      this.closeModal();
    }
  }

  closeModal(): void {
    this.submitted = false;
    this.form.reset();
    this.close.emit();
  }

  getFieldError(fieldName: string): string {
    const control = this.form.get(fieldName);
    if (!control || !this.submitted || !control.errors) {
      return '';
    }

    if (control.hasError('required')) {
      return `${this.getFieldLabel(fieldName)} es obligatorio`;
    }
    if (control.hasError('minlength')) {
      return `${this.getFieldLabel(fieldName)} debe tener al menos 3 caracteres`;
    }
    if (control.hasError('pattern')) {
      return `${this.getFieldLabel(fieldName)} tiene un formato inválido`;
    }
    if (control.hasError('email')) {
      return 'El correo electrónico no es válido';
    }

    return 'Error en el campo';
  }

  private getFieldLabel(fieldName: string): string {
    const labels: { [key: string]: string } = {
      nombre: 'Nombre de la Empresa',
      nit: 'NIT',
      direccion: 'Dirección',
      telefono: 'Teléfono',
      correo: 'Correo Electrónico'
    };
    return labels[fieldName] || fieldName;
  }

  isFieldInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return this.submitted && control !== null && (control.invalid || control.errors !== null);
  }
}
