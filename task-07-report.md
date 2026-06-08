# TASK-07-REPORT

**Fecha:** 21 de mayo de 2026
**Estado:** ✅ COMPLETADO

## Resumen

Se implementó el Módulo de Vehículos en Angular 18 siguiendo el mismo patrón usado por Empresas y Conductores: servicio mock CRUD, módulo lazy-loaded, componente de listado con filtros/búsqueda/paginación y modal reactivo con validaciones y dropdowns de empresa y conductor.

## Archivos creados

- `src/app/core/services/vehicle.service.ts`
- `src/app/features/admin/vehicles/vehicles.module.ts`
- `src/app/features/admin/vehicles/vehicles-routing.module.ts`
- `src/app/features/admin/vehicles/vehicles/vehicles.component.ts`
- `src/app/features/admin/vehicles/vehicles/vehicles.component.html`
- `src/app/features/admin/vehicles/vehicles/vehicles.component.css`
- `src/app/shared/components/vehicle-form-modal/vehicle-form-modal.component.ts`
- `src/app/shared/components/vehicle-form-modal/vehicle-form-modal.component.html`
- `src/app/shared/components/vehicle-form-modal/vehicle-form-modal.component.css`

## Archivos modificados

- `src/app/features/admin/admin/admin-routing.module.ts`
- `src/app/shared/shared.module.ts`

## Cambios realizados

- Se creó `VehicleService` con 3 vehículos mock iniciales:
  - `XYZ-123` - Kenworth T800 - 32.00 - Acerías Paz del Río - Jaime Galindo - Disponible
  - `ABC-456` - Freightliner Cascadia - 28.50 - Acerías Paz del Río - Sebastián Torres - En Viaje
  - `DEF-789` - International LT625 - 30.00 - TransCarga S.A. - Carlos Mendoza - Inactivo
- Se implementó paginación, búsqueda por placa/marca/conductor y filtro por estado.
- Se creó `VehiclesModule` con lazy loading en `/admin/vehicles`.
- Se creó `VehiclesComponent` con listado, búsqueda, filtros, paginación y acciones CRUD.
- Se creó `VehicleFormModalComponent` con formulario reactivo, validaciones, carga asíncrona de empresas y conductores, y validación de placa única.
- Se registró el modal en `SharedModule`.
- Se agregó la ruta lazy en `admin-routing.module.ts`.
- El sidebar ya tenía el enlace a `/admin/vehicles`, por lo que no requirió cambios.

## Comandos ejecutados

```powershell
cd "c:\Users\camil\Desktop\Semestre curso\Ingeniería de Software II\Proyecto_Gestion_Automoviles\frontend\transport-app"
ng build --configuration=development
```

## Resultados de validación

### Build

- `ng build --configuration=development` finalizó correctamente.
- El bundle lazy `vehicles-module` se generó sin errores AOT.

### Pruebas manuales en navegador

Se verificó en `http://localhost:4200/admin/vehicles`:

- La página carga correctamente.
- La tabla muestra los 3 vehículos mock iniciales.
- Los filtros por estado están disponibles.
- La búsqueda por placa, marca o conductor funciona.
- El modal de creación abre correctamente.
- Se pudo crear un vehículo de prueba (`GHI-321`) y la tabla se actualizó.
- Se pudo eliminar el vehículo de prueba y la tabla volvió al estado inicial.

## Errores y soluciones

- No hubo errores de compilación después de la implementación.
- Se evitó mezclar componentes standalone con NgModules usando `standalone: false` en los componentes declarados en módulos.
- Se corrigió el modal de vehículos para evitar duplicar encabezados visuales y mantener el patrón de `app-modal`.

## Conclusión

La implementación quedó completa y validada. El build es exitoso y la navegación a `/admin/vehicles` funciona con CRUD mock operativo.
