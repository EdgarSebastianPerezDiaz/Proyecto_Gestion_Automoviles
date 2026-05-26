import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { User, UserService } from '../../../../core/services/user.service';

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css'],
  standalone: false
})
export class UsersComponent implements OnInit {
  Math = Math;
  users: User[] = [];
  total = 0;
  page = 1;
  limit = 10;
  search = '';
  roleFilter: 'todos' | 'administrador' | 'operario' = 'todos';

  showModal = false;
  editingUser: User | null = null;

  constructor(
    private userService: UserService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    console.log('Cargando usuarios con filtro:', this.roleFilter, 'busqueda:', this.search);
    this.userService.getUsers(this.page, this.limit, this.search, this.roleFilter === 'todos' ? 'todos' : this.roleFilter).subscribe((res: any) => {
      console.log('Usuarios recibidos:', res);
      this.users = res.items;
      this.total = res.total;
      this.cdr.detectChanges();
    });
  }

  onSearch(value: string): void {
    this.search = value;
    this.page = 1;
    this.load();
  }

  setRoleFilter(role: 'todos' | 'administrador' | 'operario') {
    this.roleFilter = role;
    this.page = 1;
    this.load();
  }

  prev(): void {
    if (this.page > 1) {
      this.page--;
      this.load();
    }
  }

  next(): void {
    if (this.page * this.limit < this.total) {
      this.page++;
      this.load();
    }
  }

  openCreate(): void {
    this.editingUser = null;
    this.showModal = true;
  }

  openEdit(user: User): void {
    this.editingUser = user;
    this.showModal = true;
  }

  onSaved(): void {
    this.showModal = false;
    this.load();
  }

  onClose(): void {
    this.showModal = false;
  }

  deleteUser(user: User): void {
    if (user.id === 'USR-001') {
      alert('El administrador principal no puede ser eliminado.');
      return;
    }
    if (!confirm(`Eliminar usuario ${user.nombre}?`)) return;
    this.userService.deleteUser(user.id).subscribe({
      next: () => this.load(),
      error: (err: any) => alert(err.message || 'Error al eliminar')
    });
  }
}
