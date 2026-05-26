import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { FulfillmentsRoutingModule } from './fulfillments-routing.module';
import { FulfillmentsComponent } from './fulfillments/fulfillments.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [FulfillmentsComponent],
  imports: [
    CommonModule,
    FulfillmentsRoutingModule,
    SharedModule
  ]
})
export class FulfillmentsModule { }
