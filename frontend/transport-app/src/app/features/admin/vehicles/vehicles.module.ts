import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

import { VehiclesRoutingModule } from './vehicles-routing.module';
import { VehiclesComponent } from './vehicles/vehicles.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [
    VehiclesComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    VehiclesRoutingModule,
    SharedModule
  ]
})
export class VehiclesModule { }
