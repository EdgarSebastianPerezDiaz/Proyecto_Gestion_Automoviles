import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { User, UserService } from '../../../core/services/user.service';

@Component({
  selector: 'app-user-form-modal',
  templateUrl: './user-form-modal.component.html',
  styleUrls: ['./user-form-modal.component.css'],
  standalone: false
})
export class UserFormModalComponent implements OnInit {
  @Input() user?: User | null;
  @Output() saved = new EventEmitter<void>();
  @Output() close = new EventEmitter<void>();

  form: FormGroup;
  isCreate = true;

  constructor(private fb: FormBuilder, private userService: UserService) {
    this.form = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      email: ['', [Validators.required, Validators.email]],
      rol: ['operario'],
      password: [''],
      confirmPassword: ['']
    });
  }

  ngOnInit(): void {
    this.isCreate = !this.user;
    if (this.user) {
      this.form.patchValue({ nombre: this.user.nombre, email: this.user.email });
      // hide role/password on edit
      this.form.get('rol')?.setValue(this.user.rol);
    } else {
      this.form.get('password')?.setValidators([Validators.required, Validators.minLength(6)]);
      this.form.get('confirmPassword')?.setValidators([Validators.required, Validators.minLength(6)]);
    }
  }

  get f(): any { return this.form.controls as any; }

  submit(): void {
    if (this.form.invalid) return;
    const val = this.form.value;
    if (this.isCreate) {
      if (val.password !== val.confirmPassword) {
        alert('Las contraseñas no coinciden');
        return;
      }
      this.userService.createUser({ nombre: val.nombre, email: val.email, rol: 'operario', ultimoAcceso: undefined, isActive: true, createdAt: new Date(), password: val.password } as any).subscribe({
        next: () => {
          this.saved.emit();
        },
        error: (err: any) => alert(err.message || 'Error creando usuario')
      });
    } else if (this.user) {
      this.userService.updateUser(this.user.id, { nombre: val.nombre, email: val.email }).subscribe({
        next: () => this.saved.emit(),
        error: (err: any) => alert(err.message || 'Error actualizando')
      });
    }
  }

  onClose(): void { this.close.emit(); }
}
