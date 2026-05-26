import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

// Components
import { NavbarComponent } from './components/navbar/navbar.component';
import { SidebarComponent } from './components/sidebar/sidebar.component';
import { KpiCardComponent } from './components/kpi-card/kpi-card.component';
import { AlertItemComponent } from './components/alert-item/alert-item.component';
import { ModalComponent } from './components/modal/modal.component';
import { CompanyFormModalComponent } from './components/company-form-modal/company-form-modal.component';
import { DriverFormModalComponent } from './components/driver-form-modal/driver-form-modal.component';
import { VehicleFormModalComponent } from './components/vehicle-form-modal/vehicle-form-modal.component';
import { FinalRecipientFormModalComponent } from './components/final-recipient-form-modal/final-recipient-form-modal.component';
import { TransportistaFormModalComponent } from './components/transportista-form-modal/transportista-form-modal.component';
import { CargoTypeFormModalComponent } from './components/cargo-type-form-modal/cargo-type-form-modal.component';
import { TripWizardModalComponent } from './components/trip-wizard-modal/trip-wizard-modal.component';
import { ChangeStatusModalComponent } from './components/change-status-modal/change-status-modal.component';
import { DocumentsModalComponent } from './components/documents-modal/documents-modal.component';
import { FulfillmentFormModalComponent } from './components/fulfillment-form-modal/fulfillment-form-modal.component';
import { FulfillmentDetailsModalComponent } from './components/fulfillment-details-modal/fulfillment-details-modal.component';
import { MarkPaymentModalComponent } from './components/mark-payment-modal/mark-payment-modal.component';
import { UserFormModalComponent } from './components/user-form-modal/user-form-modal.component';

@NgModule({
  declarations: [
    NavbarComponent,
    SidebarComponent,
    KpiCardComponent,
    AlertItemComponent,
    ModalComponent,
    CompanyFormModalComponent,
    DriverFormModalComponent,
    VehicleFormModalComponent,
    FinalRecipientFormModalComponent,
    TransportistaFormModalComponent,
    CargoTypeFormModalComponent,
    TripWizardModalComponent,
    ChangeStatusModalComponent,
    DocumentsModalComponent,
    FulfillmentFormModalComponent,
    FulfillmentDetailsModalComponent,
    MarkPaymentModalComponent
    ,UserFormModalComponent
  ],
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    FormsModule
  ],
  exports: [
    NavbarComponent,
    SidebarComponent,
    KpiCardComponent,
    AlertItemComponent,
    ModalComponent,
    CompanyFormModalComponent,
    DriverFormModalComponent,
    VehicleFormModalComponent,
    FinalRecipientFormModalComponent,
    TransportistaFormModalComponent,
    CargoTypeFormModalComponent,
    TripWizardModalComponent,
    ChangeStatusModalComponent,
    DocumentsModalComponent,
    FulfillmentFormModalComponent,
    FulfillmentDetailsModalComponent,
    MarkPaymentModalComponent
    ,UserFormModalComponent
  ]
})
export class SharedModule { }
