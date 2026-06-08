import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { AuditService, AuditOperation, AuditLogin } from '../../../../core/services/audit.service';
import { ExportService } from '../../../../core/services/export.service';

@Component({
  selector: 'app-audit',
  templateUrl: './audit.component.html',
  styleUrls: ['./audit.component.css'],
  standalone: false
})
export class AuditComponent implements OnInit {
  activeTab: 'operations' | 'logins' = 'operations';
  public Math = Math;

  // operations
  operations: AuditOperation[] = [];
  totalOperations = 0;
  pageOp = 1;
  limitOp = 10;
  searchOp = '';
  actionFilter: 'todos' | 'INSERT' | 'UPDATE' | 'DELETE' = 'todos';
  loadingOp = false;

  // logins
  logins: AuditLogin[] = [];
  totalLogins = 0;
  pageLog = 1;
  limitLog = 10;
  searchLog = '';
  loadingLog = false;

  constructor(
    private auditService: AuditService,
    private exportService: ExportService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadOperations();
    this.loadLogins();
  }

  switchTab(tab: 'operations' | 'logins') {
    this.activeTab = tab;
  }

  // Operations
  loadOperations() {
    console.log('Cargando operaciones...');
    this.loadingOp = true;
    this.auditService.getOperations(this.pageOp, this.limitOp, this.searchOp, this.actionFilter).subscribe(res => {
      console.log('Operaciones recibidas:', res.items);
      this.operations = res.items;
      this.totalOperations = res.total;
      this.loadingOp = false;
      this.cdr.detectChanges();
    });
  }

  onSearchOp(term: string) {
    this.searchOp = term;
    this.pageOp = 1;
    this.loadOperations();
  }

  setActionFilter(filter: 'todos' | 'INSERT' | 'UPDATE' | 'DELETE') {
    this.actionFilter = filter;
    this.pageOp = 1;
    this.loadOperations();
  }

  prevOp() {
    if (this.pageOp > 1) { this.pageOp--; this.loadOperations(); }
  }
  nextOp() {
    if (this.pageOp < Math.ceil(this.totalOperations / this.limitOp)) { this.pageOp++; this.loadOperations(); }
  }

  exportAllOperations() {
    this.auditService.getAllOperationsForExport(this.searchOp, this.actionFilter).subscribe(list => {
      const rows = list.map(i => ({
        id: i.id,
        fechaHora: i.fechaHora,
        tablaAfectada: i.tablaAfectada,
        idRegistroAfectado: i.idRegistroAfectado,
        accion: i.accion,
        usuarioResponsable: i.usuarioResponsable
      }));
      this.exportService.exportToCSV(rows, `audit-operations-${new Date().toISOString()}.csv`);
    });
  }

  exportOperationRow(op: AuditOperation) {
    this.exportService.exportToCSV([op], `audit-operation-${op.id}.csv`);
  }

  // Logins
  loadLogins() {
    console.log('Cargando logins...');
    this.loadingLog = true;
    this.auditService.getLogins(this.pageLog, this.limitLog, this.searchLog).subscribe(res => {
      console.log('Logins recibidos:', res.items);
      this.logins = res.items;
      this.totalLogins = res.total;
      this.loadingLog = false;
      this.cdr.detectChanges();
    });
  }

  onSearchLog(term: string) {
    this.searchLog = term;
    this.pageLog = 1;
    this.loadLogins();
  }

  prevLog() { if (this.pageLog > 1) { this.pageLog--; this.loadLogins(); } }
  nextLog() { if (this.pageLog < Math.ceil(this.totalLogins / this.limitLog)) { this.pageLog++; this.loadLogins(); } }

  exportAllLogins() {
    this.auditService.getAllLoginsForExport(this.searchLog).subscribe(list => {
      this.exportService.exportToCSV(list.map(l => ({ id: l.id, usuario: l.usuario, fechaHora: l.fechaHora })), `audit-logins-${new Date().toISOString()}.csv`);
    });
  }

  exportLoginRow(l: AuditLogin) {
    this.exportService.exportToCSV([l], `audit-login-${l.id}.csv`);
  }
}
