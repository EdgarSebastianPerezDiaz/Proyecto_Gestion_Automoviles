import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { CargoTypesRoutingModule } from './cargo-types-routing.module';
import { CargoTypesComponent } from './cargo-types/cargo-types.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [CargoTypesComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    CargoTypesRoutingModule,
    SharedModule
  ]
})
export class CargoTypesModule { }
