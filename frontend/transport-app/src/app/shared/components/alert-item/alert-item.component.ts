import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-alert-item',
  templateUrl: './alert-item.component.html',
  styleUrl: './alert-item.component.css',
  standalone: false
})
export class AlertItemComponent {
  @Input() severity: 'error' | 'warning' | 'info' = 'info';
  @Input() message: string = '';
  @Input() link?: string;
  @Input() timestamp?: Date;
  @Output() clicked = new EventEmitter<void>();

  constructor(private router: Router) {}

  handleClick(): void {
    this.clicked.emit();
    if (this.link) {
      this.router.navigate([this.link]);
    }
  }

  getIcon(): string {
    const icons: { [key: string]: string } = {
      'error': '🔴',
      'warning': '🟡',
      'info': '🔵'
    };
    return icons[this.severity] || icons['info'];
  }

  getBackgroundColor(): string {
    const colors: { [key: string]: string } = {
      'error': 'bg-red-50 border-red-300 text-red-900',
      'warning': 'bg-yellow-50 border-yellow-300 text-yellow-900',
      'info': 'bg-blue-50 border-blue-300 text-blue-900'
    };
    return colors[this.severity] || colors['info'];
  }

  formatTime(): string {
    if (!this.timestamp) return '';
    const now = new Date();
    const diff = Math.floor((now.getTime() - this.timestamp.getTime()) / 1000);
    
    if (diff < 60) return 'hace unos segundos';
    if (diff < 3600) return `hace ${Math.floor(diff / 60)} minutos`;
    if (diff < 86400) return `hace ${Math.floor(diff / 3600)} horas`;
    return `hace ${Math.floor(diff / 86400)} días`;
  }
}
