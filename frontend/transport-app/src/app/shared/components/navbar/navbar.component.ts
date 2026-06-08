import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { CommonModule } from '@angular/common';
import { SidebarToggleService } from '../../services/sidebar-toggle.service';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css',
  standalone: false
})
export class NavbarComponent implements OnInit {
  userName: string = '';
  userRole: string = '';

  constructor(
    private authService: AuthService,
    private router: Router,
    private sidebarToggleService: SidebarToggleService
  ) {}

  ngOnInit(): void {
    this.loadUserInfo();
  }

  loadUserInfo(): void {
    const user = this.authService.getUser();
    this.userName = user?.full_name || 'Usuario';
    this.userRole = this.authService.getUserRole() || 'user';
  }

  toggleSidebar(): void {
    this.sidebarToggleService.toggle();
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        // ensure local cleanup and navigate
        try { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); localStorage.removeItem('user_data'); } catch {}
        this.router.navigate(['/login']);
      },
      error: () => {
        try { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); localStorage.removeItem('user_data'); } catch {}
        this.router.navigate(['/login']);
      }
    });
  }
}
