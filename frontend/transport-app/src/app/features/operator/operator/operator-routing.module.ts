import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { OperatorDashboardComponent } from '../dashboard/dashboard.component';

const routes: Routes = [
  { path: 'dashboard', component: OperatorDashboardComponent },
  { path: 'companies', loadChildren: () => import('../../admin/companies/companies.module').then(m => m.CompaniesModule) },
  { path: 'final-recipients', loadChildren: () => import('../../admin/final-recipients/final-recipients.module').then(m => m.FinalRecipientsModule) },
  { path: 'transportistas', loadChildren: () => import('../../admin/transportistas/transportistas.module').then(m => m.TransportistasModule) },
  { path: 'drivers', loadChildren: () => import('../../admin/drivers/drivers.module').then(m => m.DriversModule) },
  { path: 'vehicles', loadChildren: () => import('../../admin/vehicles/vehicles.module').then(m => m.VehiclesModule) },
  { path: 'cargo-types', loadChildren: () => import('../../admin/cargo-types/cargo-types.module').then(m => m.CargoTypesModule) },
  { path: 'trips', loadChildren: () => import('../../admin/trips/trips.module').then(m => m.TripsModule) },
  { path: 'fulfillments', loadChildren: () => import('../../admin/fulfillments/fulfillments.module').then(m => m.FulfillmentsModule) },
  { path: 'documents-generated', loadChildren: () => import('../../admin/documents-generated/documents-generated.module').then(m => m.DocumentsGeneratedModule) },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class OperatorRoutingModule { }
