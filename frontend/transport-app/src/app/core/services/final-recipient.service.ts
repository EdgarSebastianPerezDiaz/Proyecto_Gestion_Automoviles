import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';

export interface FinalRecipient {
  id: string;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  correo: string;
}

const MOCK_FINAL_RECIPIENTS: FinalRecipient[] = [
  { id: 'FR1', nombre: 'Metro de Bogotá S.A.S.', nit: '900.123.456-7', direccion: 'Calle 26 # 59-51, Bogotá', telefono: '(601) 123 4567', correo: 'compras@metrobogota.gov.co' },
  { id: 'FR2', nombre: 'Homecenter Sodimac', nit: '800.987.654-3', direccion: 'Autopista Norte # 223-45, Bogotá', telefono: '(601) 987 6543', correo: 'logistica@homecenter.com' },
  { id: 'FR3', nombre: 'Almacenes Éxito S.A.', nit: '890.555.222-1', direccion: 'Carrera 68D # 80-20, Bogotá', telefono: '(601) 555 2222', correo: 'centrodistribucion@exito.com.co' }
];

@Injectable({
  providedIn: 'root'
})
export class FinalRecipientService {
  private finalRecipients: FinalRecipient[] = [...MOCK_FINAL_RECIPIENTS];
  private nextId = 4;

  getAll(): Observable<FinalRecipient[]> {
    return of(this.finalRecipients.map(recipient => ({ ...recipient }))).pipe(delay(300));
  }

  getById(id: string): Observable<FinalRecipient | undefined> {
    return of(this.finalRecipients.find(recipient => recipient.id === id)).pipe(
      delay(300),
      map(recipient => recipient ? { ...recipient } : undefined)
    );
  }

  create(finalRecipient: Omit<FinalRecipient, 'id'>): Observable<FinalRecipient> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const created: FinalRecipient = { ...finalRecipient, id: `FR${this.nextId}` };
        this.nextId++;
        this.finalRecipients.push(created);
        return { ...created };
      })
    );
  }

  update(id: string, updates: Partial<FinalRecipient>): Observable<FinalRecipient> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.finalRecipients.findIndex(recipient => recipient.id === id);
        if (index === -1) {
          throw new Error(`FinalRecipient with id ${id} not found`);
        }

        this.finalRecipients[index] = { ...this.finalRecipients[index], ...updates, id };
        return { ...this.finalRecipients[index] };
      })
    );
  }

  delete(id: string): Observable<void> {
    return of(null).pipe(
      delay(300),
      map(() => {
        const index = this.finalRecipients.findIndex(recipient => recipient.id === id);
        if (index > -1) {
          this.finalRecipients.splice(index, 1);
        }
      })
    );
  }
}
