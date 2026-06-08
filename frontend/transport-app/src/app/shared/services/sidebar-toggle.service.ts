import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SidebarToggleService {
  private readonly sidebarOpenSubject = new BehaviorSubject<boolean>(false);
  readonly sidebarOpen$ = this.sidebarOpenSubject.asObservable();

  toggle(): void {
    this.sidebarOpenSubject.next(!this.sidebarOpenSubject.value);
  }

  close(): void {
    this.sidebarOpenSubject.next(false);
  }
}