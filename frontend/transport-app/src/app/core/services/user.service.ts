import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

export interface User {
  id: string;
  nombre: string;
  email?: string;
  rol: 'administrador' | 'operario';
  ultimoAcceso?: Date;
  isActive: boolean;
  createdAt: Date;
}

interface UserSeed {
  id: string;
  nombre: string;
  email?: string;
  rol: 'administrador' | 'operario';
  ultimoAcceso?: string;
}

const SEED_USERS: UserSeed[] = [
  { id: 'USR-001', nombre: 'Juan García', email: 'juan.garcia@example.com', rol: 'administrador', ultimoAcceso: '2026-03-11T18:03:00' },
  { id: 'USR-002', nombre: 'Carlos Pérez', email: 'carlos.perez@example.com', rol: 'operario', ultimoAcceso: '2026-03-11T07:58:00' },
  { id: 'USR-003', nombre: 'María Suárez', email: 'maria.suarez@example.com', rol: 'operario', ultimoAcceso: '2026-03-09T14:22:00' }
];

@Injectable({ providedIn: 'root' })
export class UserService {
  private users: User[] = [];
  private nextSeq = 4;

  constructor() {
    this.users = SEED_USERS.map(u => ({
      id: u.id,
      nombre: u.nombre,
      email: u.email,
      rol: u.rol,
      ultimoAcceso: u.ultimoAcceso ? new Date(u.ultimoAcceso) : undefined,
      isActive: true,
      createdAt: new Date()
    }));
  }

  private generateId(): string {
    const id = `USR-${String(this.nextSeq).padStart(3, '0')}`;
    this.nextSeq++;
    return id;
  }

  getUsers(page = 1, limit = 10, search = '', rolFilter: 'administrador' | 'operario' | 'todos' = 'todos'): Observable<{ items: User[]; total: number }> {
    return of(null).pipe(
      delay(200),
      map(() => {
        let filtered = [...this.users];
        if (rolFilter !== 'todos') {
          filtered = filtered.filter(u => u.rol === rolFilter);
        }
        if (search && search.trim()) {
          const term = search.toLowerCase().trim();
          filtered = filtered.filter(u => u.nombre.toLowerCase().includes(term) || (u.email || '').toLowerCase().includes(term) || u.id.toLowerCase().includes(term));
        }
        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit);
        return { items, total };
      })
    );
  }

  getUserById(id: string): Observable<User | undefined> {
    return of(this.users.find(u => u.id === id)).pipe(delay(150));
  }

  createUser(payload: Omit<User, 'id' | 'createdAt' | 'isActive'> & { password: string }): Observable<User> {
    return of(null).pipe(
      delay(200),
      map(() => {
        // Email uniqueness check (mock)
        if (payload.email && this.users.some(u => u.email === payload.email)) {
          throw new Error('Email already exists');
        }

        const id = this.generateId();
        const user: User = {
          id,
          nombre: payload.nombre,
          email: payload.email,
          rol: 'operario',
          ultimoAcceso: undefined,
          isActive: true,
          createdAt: new Date()
        };
        // Simulate storing password (mock)
        // In real system, never store plain password in frontend
        (user as any)._mockPassword = payload.password;
        this.users.push(user);
        return user;
      })
    );
  }

  updateUser(id: string, updates: Partial<User>): Observable<User> {
    return of(null).pipe(
      delay(150),
      map(() => {
        const index = this.users.findIndex(u => u.id === id);
        if (index === -1) throw new Error('User not found');
        // Do not allow role changes via update to avoid creating admins
        const current = this.users[index];
        const updated: User = {
          ...current,
          nombre: updates.nombre ?? current.nombre,
          email: updates.email ?? current.email,
          // rol: current.rol,
          ultimoAcceso: updates.ultimoAcceso ?? current.ultimoAcceso,
          isActive: updates.isActive ?? current.isActive
        };
        this.users[index] = updated;
        return updated;
      })
    );
  }

  deleteUser(id: string): Observable<boolean> {
    return of(null).pipe(
      delay(150),
      map(() => {
        if (id === 'USR-001') {
          throw new Error('Cannot delete primary administrator');
        }
        const idx = this.users.findIndex(u => u.id === id);
        if (idx === -1) throw new Error('User not found');
        this.users.splice(idx, 1);
        return true;
      })
    );
  }

  getAdminPrincipal(): Observable<User | undefined> {
    return of(this.users.find(u => u.id === 'USR-001')).pipe(delay(100));
  }
}
