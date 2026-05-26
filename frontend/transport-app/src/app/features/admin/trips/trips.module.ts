import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';

import { TripsRoutingModule } from './trips-routing.module';
import { TripsComponent } from './trips/trips.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [TripsComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TripsRoutingModule,
    SharedModule
  ]
})
export class TripsModule { }
