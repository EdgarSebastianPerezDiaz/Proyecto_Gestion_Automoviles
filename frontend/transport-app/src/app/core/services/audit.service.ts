import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';

export interface AuditOperation {
  id: string;
  fechaHora: Date;
  tablaAfectada: string;
  idRegistroAfectado: string;
  accion: 'INSERT' | 'UPDATE' | 'DELETE';
  usuarioResponsable: string;
}

export interface AuditLogin {
  id: string;
  usuario: string;
  fechaHora: Date;
}

@Injectable({ providedIn: 'root' })
export class AuditService {
  private operations: AuditOperation[] = [];
  private logins: AuditLogin[] = [];

  constructor() {
    this.buildMockData();
  }

  private buildMockData(): void {
    // Seed with the specific examples requested
    const ops: AuditOperation[] = [
      { id: 'OP-001', fechaHora: new Date(2026, 2, 11, 8, 14, 32), tablaAfectada: 'viajes', idRegistroAfectado: 'VJ-004', accion: 'INSERT', usuarioResponsable: 'Carlos Pérez (Operario)' },
      { id: 'OP-002', fechaHora: new Date(2026, 2, 11, 9, 45, 10), tablaAfectada: 'vehiculos', idRegistroAfectado: 'XYZ-123', accion: 'UPDATE', usuarioResponsable: 'Carlos Pérez (Operario)' },
      { id: 'OP-003', fechaHora: new Date(2026, 2, 10, 17, 22, 5), tablaAfectada: 'conductores', idRegistroAfectado: 'CON-007', accion: 'DELETE', usuarioResponsable: 'Juan García (Administrador)' },
      { id: 'OP-004', fechaHora: new Date(2026, 2, 10, 10, 15, 0), tablaAfectada: 'empresas', idRegistroAfectado: 'EMP-003', accion: 'UPDATE', usuarioResponsable: 'María Suárez (Operario)' },
      { id: 'OP-005', fechaHora: new Date(2026, 2, 9, 14, 30, 0), tablaAfectada: 'tipos_carga', idRegistroAfectado: 'CAR-002', accion: 'DELETE', usuarioResponsable: 'Juan García (Administrador)' },
      { id: 'OP-006', fechaHora: new Date(2026, 2, 9, 9, 0, 0), tablaAfectada: 'cumplidos', idRegistroAfectado: 'CUM-001', accion: 'UPDATE', usuarioResponsable: 'Juan García (Administrador)' },
      { id: 'OP-007', fechaHora: new Date(2026, 2, 8, 18, 45, 0), tablaAfectada: 'usuarios', idRegistroAfectado: 'USR-002', accion: 'INSERT', usuarioResponsable: 'Juan García (Administrador)' }
    ];

    // Add additional mock records up to ~35
    const tables = ['empresas','conductores','vehiculos','viajes','cumplidos','tipos_carga','usuarios'];
    const users = ['Carlos Pérez (Operario)','María Suárez (Operario)','Juan García (Administrador)','Ana López (Operario)'];
    let counter = 8;

    for (let i = 0; i < 30; i++) {
      const daysAgo = Math.floor(Math.random() * 28);
      const d = new Date();
      d.setDate(d.getDate() - daysAgo);
      d.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60), Math.floor(Math.random() * 60));
      const table = tables[i % tables.length];
      const action: AuditOperation['accion'] = (['INSERT','UPDATE','DELETE'] as const)[i % 3];
      const idReg = `${table.substring(0,3).toUpperCase()}-${100 + i}`;
      const user = users[i % users.length];
      ops.push({ id: `OP-${String(counter).padStart(3,'0')}`, fechaHora: d, tablaAfectada: table, idRegistroAfectado: idReg, accion: action, usuarioResponsable: user });
      counter++;
    }

    // Sort descending by fechaHora
    this.operations = ops.sort((a,b) => b.fechaHora.getTime() - a.fechaHora.getTime());

    // Build logins (20-25)
    const logs: AuditLogin[] = [];
    const loginUsers = ['Carlos Pérez (Operario)','Juan García (Administrador)','María Suárez (Operario)','Ana López (Operario)'];
    let logCounter = 46; // to match examples like LOG-048
    for (let i = 0; i < 22; i++) {
      const daysAgo = Math.floor(Math.random() * 28);
      const d = new Date();
      d.setDate(d.getDate() - daysAgo);
      d.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60), Math.floor(Math.random() * 60));
      logs.push({ id: `LOG-${String(logCounter).padStart(3,'0')}`, usuario: loginUsers[i % loginUsers.length], fechaHora: d });
      logCounter--;
    }

    // include explicit examples
    logs[0] = { id: 'LOG-048', usuario: 'Carlos Pérez (Operario)', fechaHora: new Date(2026,2,11,7,58,44) };
    logs[1] = { id: 'LOG-047', usuario: 'Juan García (Administrador)', fechaHora: new Date(2026,2,10,18,3,12) };
    logs[2] = { id: 'LOG-046', usuario: 'Carlos Pérez (Operario)', fechaHora: new Date(2026,2,10,7,51,9) };
    logs[3] = { id: 'LOG-045', usuario: 'María Suárez (Operario)', fechaHora: new Date(2026,2,9,8,30,0) };
    logs[4] = { id: 'LOG-044', usuario: 'Juan García (Administrador)', fechaHora: new Date(2026,2,9,8,0,0) };

    this.logins = logs.sort((a,b) => b.fechaHora.getTime() - a.fechaHora.getTime());
  }

  getOperations(page = 1, limit = 10, search = '', actionFilter: 'todos' | 'INSERT' | 'UPDATE' | 'DELETE' = 'todos') {
    let filtered = this.operations.slice();
    const s = (search || '').trim().toLowerCase();
    if (s) {
      filtered = filtered.filter(o =>
        o.tablaAfectada.toLowerCase().includes(s) ||
        o.idRegistroAfectado.toLowerCase().includes(s) ||
        o.usuarioResponsable.toLowerCase().includes(s)
      );
    }
    if (actionFilter !== 'todos') {
      filtered = filtered.filter(o => o.accion === actionFilter);
    }

    const total = filtered.length;
    const start = (page - 1) * limit;
    const items = filtered.slice(start, start + limit);
    return of({ items, total }).pipe(delay(300));
  }

  getLogins(page = 1, limit = 10, search = '') {
    let filtered = this.logins.slice();
    const s = (search || '').trim().toLowerCase();
    if (s) {
      filtered = filtered.filter(l => l.usuario.toLowerCase().includes(s));
    }
    const total = filtered.length;
    const start = (page - 1) * limit;
    const items = filtered.slice(start, start + limit);
    return of({ items, total }).pipe(delay(300));
  }

  getAllOperationsForExport(search = '', actionFilter: 'todos' | 'INSERT' | 'UPDATE' | 'DELETE' = 'todos') {
    let filtered = this.operations.slice();
    const s = (search || '').trim().toLowerCase();
    if (s) {
      filtered = filtered.filter(o =>
        o.tablaAfectada.toLowerCase().includes(s) ||
        o.idRegistroAfectado.toLowerCase().includes(s) ||
        o.usuarioResponsable.toLowerCase().includes(s)
      );
    }
    if (actionFilter !== 'todos') {
      filtered = filtered.filter(o => o.accion === actionFilter);
    }
    return of(filtered).pipe(delay(300));
  }

  getAllLoginsForExport(search = '') {
    let filtered = this.logins.slice();
    const s = (search || '').trim().toLowerCase();
    if (s) {
      filtered = filtered.filter(l => l.usuario.toLowerCase().includes(s));
    }
    return of(filtered).pipe(delay(300));
  }
}
