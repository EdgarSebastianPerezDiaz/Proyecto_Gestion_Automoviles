import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

export interface Company {
  id: string;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  correo: string;
}

export interface PaginatedCompanies {
  items: Company[];
  total: number;
}

const MOCK_COMPANIES: Company[] = [
  { id: '1', nombre: 'Acerías Paz del Río', nit: '800.251.440-0', direccion: 'Vía Paz del Río, Boyacá', telefono: '(608) 770 0000', correo: 'info@acerias.com' },
  { id: '2', nombre: 'TransCarga S.A.', nit: '900.112.233-1', direccion: 'Cra 5 #12-34, Tunja', telefono: '310 444 5566', correo: 'contacto@transcarga.co' },
  { id: '3', nombre: 'Logística del Norte', nit: '901.334.556-7', direccion: 'Av. Colón #8-20, Sogamoso', telefono: '320 777 8899', correo: 'info@lognorte.com' }
];

@Injectable({
  providedIn: 'root'
})
export class CompanyService {
  private companies: Company[] = [...MOCK_COMPANIES];
  private nextId: number = 4;

  constructor() { }

  /**
   * Obtiene empresas con paginación y búsqueda
   * @param page - Número de página (comienza en 1)
   * @param limit - Cantidad de registros por página
   * @param search - Término de búsqueda (filtra por nombre o NIT)
   */
  getCompanies(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedCompanies> {
    return of(null).pipe(
      delay(500),
      map(() => {
        // Filtrar por búsqueda
        let filtered = this.companies;
        if (search.trim()) {
          filtered = this.companies.filter(c =>
            c.nombre.toLowerCase().includes(search.toLowerCase()) ||
            c.nit.includes(search)
          );
        }

        // Calcular paginación
        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit);

        return { items, total };
      })
    );
  }

  /**
   * Obtiene una empresa por ID
   */
  getCompanyById(id: string): Observable<Company | undefined> {
    return of(null).pipe(
      delay(300),
      map(() => this.companies.find(c => c.id === id))
    );
  }

  /**
   * Crea una nueva empresa
   */
  createCompany(company: Omit<Company, 'id'>): Observable<Company> {
    return of(null).pipe(
      delay(500),
      map(() => {
        const newCompany: Company = {
          ...company,
          id: this.nextId.toString()
        };
        this.nextId++;
        this.companies.push(newCompany);
        return newCompany;
      })
    );
  }

  /**
   * Actualiza una empresa existente
   */
  updateCompany(id: string, updates: Partial<Company>): Observable<Company> {
    return of(null).pipe(
      delay(500),
      map(() => {
        const index = this.companies.findIndex(c => c.id === id);
        if (index > -1) {
          this.companies[index] = { ...this.companies[index], ...updates };
          return this.companies[index];
        }
        throw new Error(`Company with id ${id} not found`);
      })
    );
  }

  /**
   * Elimina una empresa
   */
  deleteCompany(id: string): Observable<void> {
    return of(null).pipe(
      delay(500),
      map(() => {
        const index = this.companies.findIndex(c => c.id === id);
        if (index > -1) {
          this.companies.splice(index, 1);
        }
      })
    );
  }
}
