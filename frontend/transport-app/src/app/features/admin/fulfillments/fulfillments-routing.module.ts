import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { FulfillmentsComponent } from './fulfillments/fulfillments.component';

const routes: Routes = [
  { path: '', component: FulfillmentsComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class FulfillmentsRoutingModule { }
