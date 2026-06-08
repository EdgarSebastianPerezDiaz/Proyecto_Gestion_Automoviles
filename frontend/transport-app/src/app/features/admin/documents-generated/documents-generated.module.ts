import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DocumentsGeneratedRoutingModule } from './documents-generated-routing.module';
import { DocumentsGeneratedComponent } from './documents-generated/documents-generated.component';
import { SharedModule } from '../../../shared/shared.module';

@NgModule({
  declarations: [DocumentsGeneratedComponent],
  imports: [
    CommonModule,
    DocumentsGeneratedRoutingModule,
    SharedModule
  ]
})
export class DocumentsGeneratedModule { }
