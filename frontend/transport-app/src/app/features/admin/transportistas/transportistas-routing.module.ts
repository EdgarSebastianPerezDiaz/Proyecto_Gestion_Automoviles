import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TransportistasComponent } from './transportistas/transportistas.component';

const routes: Routes = [
  { path: '', component: TransportistasComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class TransportistasRoutingModule { }
