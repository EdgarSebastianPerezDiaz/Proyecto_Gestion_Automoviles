import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { OperatorRoutingModule } from './operator-routing.module';
import { OperatorDashboardComponent } from '../dashboard/dashboard.component';
import { SharedModule } from '../../../shared/shared.module';


@NgModule({
  declarations: [
    OperatorDashboardComponent
  ],
  imports: [
    CommonModule,
    OperatorRoutingModule,
    SharedModule
  ]
})
export class OperatorModule { }
