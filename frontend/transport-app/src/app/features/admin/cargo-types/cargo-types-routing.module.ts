import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CargoTypesComponent } from './cargo-types/cargo-types.component';

const routes: Routes = [{ path: '', component: CargoTypesComponent }];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class CargoTypesRoutingModule { }
