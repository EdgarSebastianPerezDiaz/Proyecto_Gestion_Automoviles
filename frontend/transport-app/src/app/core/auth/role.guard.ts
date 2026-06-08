import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

export const roleGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const requiredRole = route.data['role'];
  const userRole = authService.getUserRole();

  if (!requiredRole) {
    // No role requirement
    return true;
  }

  if (userRole === requiredRole) {
    return true;
  } else {
    // Redirect to appropriate dashboard based on user role
    if (userRole === 'admin') {
      router.navigate(['/admin/dashboard']);
    } else if (userRole === 'operator') {
      router.navigate(['/operator/dashboard']);
    } else {
      router.navigate(['/login']);
    }
    return false;
  }
};
