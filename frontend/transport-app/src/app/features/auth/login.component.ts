import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: false,
  template: `
    <div class="min-h-screen flex">
      <!-- Columna izquierda: Branding (dorado) -->
      <div class="hidden lg:flex lg:w-1/2 bg-gold flex-col justify-center items-center text-white p-12">
        <div class="max-w-md text-center">
          <h1 class="text-5xl font-extrabold mb-4">TRANSPORTES ABC</h1>
          <p class="text-xl opacity-90 mb-8">Sistema Integral de Gestión de Transporte de Carga Pesada</p>
          <div class="w-20 h-1 bg-white mx-auto mb-8"></div>
          <p class="text-sm">Gestión de viajes · Conductores · Vehículos<br>Facturación · Auditoría · Reportes</p>
        </div>
      </div>

      <!-- Columna derecha: Formulario (blanco) -->
      <div class="flex-1 flex items-center justify-center p-8 bg-white">
        <div class="w-full max-w-md">
          <!-- Header para mobile -->
          <div class="text-center mb-8 lg:hidden">
            <h1 class="text-3xl font-bold text-darkBlue">TRANSPORTES ABC</h1>
            <p class="text-gray-500 mt-2">Inicia sesión en tu cuenta</p>
          </div>

          <!-- Card del formulario -->
          <div class="card-brutal p-8">
            <h2 class="text-2xl font-bold text-darkBlue mb-2">Iniciar Sesión</h2>
            <p class="text-gray-500 mb-6">Ingresa tus credenciales para acceder al sistema</p>

            <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
              <!-- Email input -->
              <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">Correo electrónico</label>
                <input type="email" formControlName="email"
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gold focus:border-gold focus:outline-none transition"
                       placeholder="usuario@ejemplo.com">
                <div *ngIf="isFieldInvalid('email')" class="text-red-500 text-xs mt-1">
                  {{ getFieldError('email') }}
                </div>
              </div>

              <!-- Password input -->
              <div class="mb-6 relative">
                <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
                <input [type]="showPassword ? 'text' : 'password'" formControlName="password"
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gold focus:border-gold focus:outline-none transition"
                       placeholder="••••••••">
                <button type="button" (click)="togglePasswordVisibility()" 
                        class="absolute right-3 top-9 text-gray-500 hover:text-gray-700">
                  {{ showPassword ? '🙈' : '👁️' }}
                </button>
                <div *ngIf="isFieldInvalid('password')" class="text-red-500 text-xs mt-1">
                  {{ getFieldError('password') }}
                </div>
              </div>

              <!-- Submit button -->
              <button type="submit" [disabled]="loginForm.invalid || isLoading"
                      class="w-full btn-gold disabled:opacity-50 disabled:cursor-not-allowed text-center">
                {{ isLoading ? 'Ingresando...' : 'INGRESAR' }}
              </button>

              <!-- Error message -->
              <div *ngIf="errorMessage" class="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-center text-sm">
                {{ errorMessage }}
              </div>
            </form>

            <!-- Demo credentials info -->
            <div class="mt-6 text-center text-xs text-gray-400">
              <p class="mb-1">Credenciales de prueba disponibles</p>
              <span>Administrador</span> · <span>Operario</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  isLoading = false;
  showPassword = false;
  errorMessage = '';
  returnUrl: string | null = null;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  ngOnInit(): void {
    // Check if already logged in
    if (this.authService.isAuthenticated()) {
      const role = this.authService.getUserRole();
      if (role === 'admin') {
        this.router.navigate(['/admin/dashboard']);
      } else if (role === 'operator') {
        this.router.navigate(['/operator/dashboard']);
      }
    }

    // Get return URL from route parameters
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || null;
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.authService.login(this.loginForm.value.email, this.loginForm.value.password).subscribe({
      next: (response) => {
        this.isLoading = false;
        console.log('LoginComponent.onSubmit success response:', response);
        const role = this.authService.getUserRole();
        if (role === 'admin') {
          this.router.navigate([this.returnUrl || '/admin/dashboard']);
        } else if (role === 'operator') {
          this.router.navigate([this.returnUrl || '/operator/dashboard']);
        } else {
          this.router.navigate(['/login']);
        }
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error.error?.message || 'Error al iniciar sesión. Por favor, verifica tus credenciales.';
        console.error('Login error:', error);
      }
    });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  isFieldInvalid(fieldName: string): boolean {
    const field = this.loginForm.get(fieldName);
    return !!(field && field.invalid && (field.dirty || field.touched));
  }

  getFieldError(fieldName: string): string {
    const field = this.loginForm.get(fieldName);
    if (!field || !field.errors) return '';

    if (field.errors['required']) {
      return `${fieldName === 'email' ? 'Correo' : 'Contraseña'} es obligatorio`;
    }
    if (field.errors['email']) {
      return 'Formato de correo inválido';
    }
    if (field.errors['minlength']) {
      return 'Mínimo 6 caracteres';
    }
    return '';
  }
}
