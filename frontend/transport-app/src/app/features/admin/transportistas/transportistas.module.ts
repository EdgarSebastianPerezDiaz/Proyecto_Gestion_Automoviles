import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

import { TransportistasRoutingModule } from './transportistas-routing.module';
import { TransportistasComponent } from './transportistas/transportistas.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [TransportistasComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    TransportistasRoutingModule,
    SharedModule
  ]
})
export class TransportistasModule { }
