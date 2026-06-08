import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { Subscription } from 'rxjs';
import { SidebarToggleService } from '../../services/sidebar-toggle.service';

interface MenuItem {
  label: string;
  path: string;
  icon: string;
}

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css',
  standalone: false
})
export class SidebarComponent implements OnInit, OnDestroy {
  userRole: string = '';
  menuItems: MenuItem[] = [];
  currentPath: string = '';
  isMobileMenuOpen = false;
  private sidebarSubscription?: Subscription;

  adminMenuItems: MenuItem[] = [
    { label: 'Dashboard', path: '/admin/dashboard', icon: '📊' },
    { label: 'EOrigen', path: '/admin/origen', icon: '🏭' },
    { label: 'EDestino', path: '/admin/destino', icon: '📍' },
    { label: 'ETransportista', path: '/admin/transportista', icon: '🚛' },
    { label: 'Conductores', path: '/admin/drivers', icon: '👨‍✈️' },
    { label: 'Vehículos', path: '/admin/vehicles', icon: '🚚' },
    { label: 'Cargas', path: '/admin/cargo-types', icon: '📦' },
    { label: 'Viajes', path: '/admin/trips', icon: '🚚' },
    { label: 'Cumplidos', path: '/admin/fulfillments', icon: '✅' },
    { label: 'Documentos', path: '/admin/documents-generated', icon: '📄' },
    { label: 'Auditoría', path: '/admin/audit', icon: '🔍' },
    { label: 'Usuarios y Roles', path: '/admin/users', icon: '👥' },
    { label: 'Reportes', path: '/admin/reports', icon: '📈' }
  ];

  operatorMenuItems: MenuItem[] = [
    { label: 'Dashboard', path: '/operator/dashboard', icon: '📊' },
    { label: 'EOrigen', path: '/operator/companies', icon: '🏭' },
    { label: 'EDestino', path: '/operator/final-recipients', icon: '📍' },
    { label: 'ETransportista', path: '/operator/transportistas', icon: '🚛' },
    { label: 'Conductores', path: '/operator/drivers', icon: '👨‍✈️' },
    { label: 'Vehículos', path: '/operator/vehicles', icon: '🚙' },
    { label: 'Cargas', path: '/operator/cargo-types', icon: '📦' },
    { label: 'Viajes', path: '/operator/trips', icon: '🚚' },
    { label: 'Cumplidos', path: '/operator/fulfillments', icon: '✅' },
    { label: 'Documentos', path: '/operator/documents-generated', icon: '📄' }
  ];

  constructor(
    private authService: AuthService,
    private router: Router,
    private sidebarToggleService: SidebarToggleService
  ) {
    this.currentPath = this.router.url;
  }

  ngOnInit(): void {
    this.userRole = this.authService.getUserRole() || 'operator';
    this.menuItems = this.userRole === 'admin' ? this.adminMenuItems : this.operatorMenuItems;
    this.sidebarSubscription = this.sidebarToggleService.sidebarOpen$.subscribe(isOpen => {
      this.isMobileMenuOpen = isOpen;
    });
  }

  ngOnDestroy(): void {
    this.sidebarSubscription?.unsubscribe();
  }

  isActive(path: string): boolean {
    return this.currentPath === path || this.currentPath.startsWith(path);
  }

  navigate(path: string): void {
    this.router.navigateByUrl(path);
    this.currentPath = path;
    this.sidebarToggleService.close();
  }
}
