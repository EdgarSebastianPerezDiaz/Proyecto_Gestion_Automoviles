import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ExportService {
  exportToCSV(data: any[], filename = 'export.csv') {
    if (!data || !data.length) {
      const blobEmpty = new Blob([""], { type: 'text/csv;charset=utf-8;' });
      this.downloadBlob(blobEmpty, filename);
      return;
    }

    const keys = Object.keys(data[0]);
    const rows = data.map(row => {
      return keys.map(k => this.escapeCsv(this.formatValue(row[k]))).join(',');
    });

    const header = keys.join(',');
    const csv = [header, ...rows].join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    this.downloadBlob(blob, filename);
  }

  private formatValue(value: any): string {
    if (value instanceof Date) {
      const d = value as Date;
      const dd = String(d.getDate()).padStart(2,'0');
      const mm = String(d.getMonth() + 1).padStart(2,'0');
      const yyyy = d.getFullYear();
      const hh = String(d.getHours()).padStart(2,'0');
      const min = String(d.getMinutes()).padStart(2,'0');
      const ss = String(d.getSeconds()).padStart(2,'0');
      return `${dd}/${mm}/${yyyy} ${hh}:${min}:${ss}`;
    }
    if (value === null || value === undefined) return '';
    return String(value);
  }

  private escapeCsv(val: string): string {
    if (val == null) return '';
    if (val.includes(',') || val.includes('"') || val.includes('\n') || val.includes('\r')) {
      return '"' + val.replace(/"/g, '""') + '"';
    }
    return val;
  }

  private downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('download', filename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
}
