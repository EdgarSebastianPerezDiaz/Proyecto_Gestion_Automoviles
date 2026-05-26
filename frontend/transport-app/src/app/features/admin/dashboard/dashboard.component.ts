import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { DashboardService, AdminDashboardData, KPI, Alert } from '../../../core/services/dashboard.service';

@Component({
  selector: 'app-admin-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
  standalone: false
})
export class AdminDashboardComponent implements OnInit {
  dashboardData: AdminDashboardData | null = null;
  kpis: KPI[] = [];
  alerts: Alert[] = [];
  isLoading = true;
  errorMessage = '';
  modalOpen = false;

  constructor(
    private dashboardService: DashboardService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.isLoading = true;
    this.dashboardService.getAdminDashboard().subscribe({
      next: (data) => {
        this.dashboardData = data;
        this.kpis = data.kpis;
        this.alerts = data.alerts;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading admin dashboard:', error);
        this.errorMessage = 'Error al cargar el dashboard';
        this.isLoading = false;
      }
    });
  }

  /**
   * Navigate to alert link or show placeholder message
   */
  handleAlertClick(link?: string): void {
    if (link) {
      this.router.navigate([link]);
    } else {
      alert('Funcionalidad próxima');
    }
  }

  /**
   * Get severity badge color
   */
  getSeverityColor(severity: string): string {
    switch (severity) {
      case 'error':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'info':
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300';
    }
  }

  /**
   * Format timestamp to relative time
   */
  formatTime(date: Date): string {
    const diff = Date.now() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Hace un momento';
    if (minutes < 60) return `Hace ${minutes}m`;
    if (hours < 24) return `Hace ${hours}h`;
    if (days < 7) return `Hace ${days}d`;
    return new Date(date).toLocaleDateString('es-CO');
  }

  openModal(): void {
    this.modalOpen = true;
  }

  closeModal(): void {
    this.modalOpen = false;
  }

  getCurrentDate(): string {
    const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
    const months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    
    const now = new Date();
    const dayName = days[now.getDay()];
    const dayNum = now.getDate();
    const monthName = months[now.getMonth()];
    const year = now.getFullYear();

    return `${dayName} ${dayNum} de ${monthName} de ${year}`;
  }
}
