import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AdminDashboardComponent } from '../dashboard/dashboard.component';

const routes: Routes = [
  { path: 'dashboard', component: AdminDashboardComponent },
  { path: 'companies', loadChildren: () => import('../companies/companies.module').then(m => m.CompaniesModule) },
  { path: 'origen', loadChildren: () => import('../companies/companies.module').then(m => m.CompaniesModule) },
  { path: 'destino', loadChildren: () => import('../final-recipients/final-recipients.module').then(m => m.FinalRecipientsModule) },
  { path: 'transportista', loadChildren: () => import('../transportistas/transportistas.module').then(m => m.TransportistasModule) },
  { path: 'drivers', loadChildren: () => import('../drivers/drivers.module').then(m => m.DriversModule) },
  { path: 'cargo-types', loadChildren: () => import('../cargo-types/cargo-types.module').then(m => m.CargoTypesModule) },
  { path: 'trips', loadChildren: () => import('../trips/trips.module').then(m => m.TripsModule) },
  { path: 'documents-generated', loadChildren: () => import('../documents-generated/documents-generated.module').then(m => m.DocumentsGeneratedModule) },
  { path: 'audit', loadChildren: () => import('../audit/audit.module').then(m => m.AuditModule) },
  { path: 'users', loadChildren: () => import('../users/users.module').then(m => m.UsersModule) },
  { path: 'reports', loadChildren: () => import('../reports/reports.module').then(m => m.ReportsModule) },
  { path: 'vehicles', loadChildren: () => import('../vehicles/vehicles.module').then(m => m.VehiclesModule) },
  { path: 'fulfillments', loadChildren: () => import('../fulfillments/fulfillments.module').then(m => m.FulfillmentsModule) },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AdminRoutingModule { }
