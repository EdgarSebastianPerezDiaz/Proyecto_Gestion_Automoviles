import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { DocumentsGeneratedComponent } from './documents-generated/documents-generated.component';

const routes: Routes = [
  { path: '', component: DocumentsGeneratedComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class DocumentsGeneratedRoutingModule { }
