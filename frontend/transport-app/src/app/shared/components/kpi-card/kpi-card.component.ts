import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-kpi-card',
  templateUrl: './kpi-card.component.html',
  styleUrl: './kpi-card.component.css',
  standalone: false
})
export class KpiCardComponent {
  @Input() label: string = '';
  @Input() value: string | number = '';
  @Input() unit?: string;
  @Input() icon: string = '';
  @Input() color: string = 'gold';

  getColorClasses(): string {
    const colorMap: { [key: string]: string } = {
      'gold': 'bg-gold text-white',
      'green': 'bg-green-500 text-white',
      'red': 'bg-red-500 text-white',
      'orange': 'bg-orange-500 text-white',
      'blue': 'bg-blue-500 text-white'
    };
    return colorMap[this.color] || colorMap['gold'];
  }
}
