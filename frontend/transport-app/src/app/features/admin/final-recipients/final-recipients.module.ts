import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

import { FinalRecipientsRoutingModule } from './final-recipients-routing.module';
import { FinalRecipientsComponent } from './final-recipients/final-recipients.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [FinalRecipientsComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    FinalRecipientsRoutingModule,
    SharedModule
  ]
})
export class FinalRecipientsModule { }
