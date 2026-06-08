# TASK-08-REPORT

**Fecha:** 21 de mayo de 2026
**Estado:** ✅ COMPLETADO

## Resumen

Se implementó el Módulo de Tipos de Carga para el área de administración siguiendo el patrón de Empresas, Conductores y Vehículos. El módulo cuenta con servicio mock en memoria, listado con búsqueda y paginación, y modal reactivo para crear/editar cargas.

## Archivos creados

- `src/app/core/services/cargo-type.service.ts`
- `src/app/features/admin/cargo-types/cargo-types.module.ts`
- `src/app/features/admin/cargo-types/cargo-types-routing.module.ts`
- `src/app/features/admin/cargo-types/cargo-types/cargo-types.component.ts`
- `src/app/features/admin/cargo-types/cargo-types/cargo-types.component.html`
- `src/app/features/admin/cargo-types/cargo-types/cargo-types.component.css`
- `src/app/shared/components/cargo-type-form-modal/cargo-type-form-modal.component.ts`
- `src/app/shared/components/cargo-type-form-modal/cargo-type-form-modal.component.html`
- `src/app/shared/components/cargo-type-form-modal/cargo-type-form-modal.component.css`

## Archivos modificados

- `src/app/features/admin/admin/admin-routing.module.ts`
- `src/app/shared/shared.module.ts`
- `src/app/shared/components/sidebar/sidebar.component.ts`

## Cambios realizados

- Se creó `CargoTypeService` con 3 registros mock iniciales.
- Se implementó CRUD en memoria con persistencia durante la sesión.
- Se añadió búsqueda local por nombre y descripción.
- Se agregó paginación local en el servicio y en el componente.
- Se creó `CargoTypesModule` con lazy loading en `/admin/cargo-types`.
- Se creó `CargoTypesComponent` con listado, búsqueda, paginación, acciones y control de permisos por rol.
- Se creó `CargoTypeFormModalComponent` con formulario reactivo y validaciones.
- Se registró el modal en `SharedModule`.
- Se integró la ruta en `admin-routing.module.ts`.
- El sidebar ya contenía el enlace a `/admin/cargo-types`, por lo que no fue necesario cambiarlo.

## Datos mock iniciales

- `CAR-001` - Acero estructural - Vigas y perfiles laminados en caliente - 28.50 - 320000
- `CAR-002` - Chatarra metálica - Retales y residuos de acero para reciclaje - 32.00 - 180000
- `CAR-003` - Tubería industrial - Tubería de acero para construcción civil - 25.00 - 290000

## Comandos ejecutados

```powershell
cd "c:\Users\camil\Desktop\Semestre curso\Ingeniería de Software II\Proyecto_Gestion_Automoviles\frontend\transport-app"
ng build --configuration=development
```

## Resultado del build

El build fue exitoso.

Salida relevante:

- `cargo-types-module` compilado correctamente.
- No se reportaron errores AOT ni de importación.

## Validación manual en navegador

Se validó en `http://localhost:4200/admin/cargo-types`:

- La tabla carga los 3 tipos de carga mock.
- La búsqueda funciona por nombre y descripción.
- La creación de un nuevo tipo de carga funciona.
- La eliminación de un tipo de carga funciona.
- La tabla vuelve a mostrar los 3 registros iniciales después de eliminar el registro de prueba.

## Evidencia funcional

- `CAR-001` - Acero estructural - `COP320,000`
- `CAR-002` - Chatarra metálica - `COP180,000`
- `CAR-003` - Tubería industrial - `COP290,000`

## Conclusión

El módulo quedó implementado y validado correctamente. La compilación es exitosa y el CRUD mock funciona en memoria en la interfaz de administración.
