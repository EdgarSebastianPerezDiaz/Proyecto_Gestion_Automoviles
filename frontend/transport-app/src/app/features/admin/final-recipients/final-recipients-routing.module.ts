import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { FinalRecipientsComponent } from './final-recipients/final-recipients.component';

const routes: Routes = [
  { path: '', component: FinalRecipientsComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class FinalRecipientsRoutingModule { }
