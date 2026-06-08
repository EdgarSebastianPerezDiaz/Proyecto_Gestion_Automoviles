# Tarea 14 - Modulo de Reportes

## Implementacion
- Se creo el modulo lazy `ReportsModule` bajo `/admin/reports`.
- Se añadió la ruta en el router de administracion.
- Se implemento la pantalla con dos tabs: `Reporte de Viajes` y `Reporte Financiero`.
- Se agregaron filtros por fecha, KPIs, bloques de grafico placeholder, tablas detalladas y exportacion CSV.
- Se ampliaron `TripService` y `FulfillmentService` con datasets mock especificos para reportes.

## Validacion
- Compilacion ejecutada con exito:
  - `ng build --configuration=development`
- Verificacion en navegador:
  - `/admin/reports` carga con navbar y sidebar.
  - El tab de viajes muestra 10 registros mock.
  - El tab financiero muestra KPIs e informacion financiera con importes en moneda.
  - El boton de exportacion quedo disponible y se ejercito sin errores visibles.

## Archivos principales
- `src/app/features/admin/admin/admin-routing.module.ts`
- `src/app/features/admin/reports/reports.module.ts`
- `src/app/features/admin/reports/reports-routing.module.ts`
- `src/app/features/admin/reports/reports/reports.component.ts`
- `src/app/features/admin/reports/reports/reports.component.html`
- `src/app/features/admin/reports/reports/reports.component.css`
- `src/app/core/services/trip.service.ts`
- `src/app/core/services/fulfillment.service.ts`