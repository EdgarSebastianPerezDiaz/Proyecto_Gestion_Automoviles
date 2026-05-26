**Informe Tarea 11 — Documentos Generados**

**Objetivo:**
- Implementar la pantalla / módulo de "Documentos Generados" para listar viajes y mostrar el conteo de documentos generados (badge X/3), permitir ver documentos existentes y reconciliar (generar faltantes).

**Cambios realizados (archivos claves):**
- `src/app/features/admin/documents-generated/documents-generated.module.ts` — módulo lazy del feature.
- `src/app/features/admin/documents-generated/documents-generated-routing.module.ts` — rutas para admin/operator.
- `src/app/features/admin/documents-generated/documents-generated/documents-generated.component.ts` — componente principal (lista, badge, botón "Ver Documentos").
- `src/app/core/services/trip.service.ts` — añadido/ajustado `reconcileDocuments()` y `buildDocuments()` para generar URLs de documentos y compatibilidad con estado legado.
- `src/app/shared/components/documents-modal/*` — reutilizado modal existente para visualizar documentos.
- `src/app/shared/shared.module.ts` — exporte/declaro el modal y componentes necesarios.

**Resumen técnico:**
- La pantalla lista viajes usando `TripService.getTrips()` y calcula el número de documentos existentes por viaje (0..3). El badge muestra el progreso visual (color según completitud).
- Al pulsar "Ver Documentos" se abre el modal `DocumentsModal` (ya existente). Desde allí o desde la pantalla se puede ejecutar la reconciliación que llama `TripService.reconcileDocuments(tripId)` para generar los documentos faltantes.
- `TripService.reconcileDocuments` invoca internamente `buildDocuments` (simulación async con RxJS) y persiste (mock) la lista actualizada; el componente recarga la lista al completar.
- Se preservó compatibilidad con la forma legacy del `Trip` y con el estado `'Completado'` (normalizado a `'Entregado'`).

**Comandos y verificaciones ejecutadas:**
- `ng build --configuration=development` — compilación AOT/production config de desarrollo: exitosa después de las correcciones.
- Navegación manual/verificación en el navegador:
  - `/admin/documents-generated` — lista de viajes, badges con conteo, apertura de modal "Ver Documentos".
  - `/operator/documents-generated` — misma pantalla con permisos operator.
  - Prueba de reconciliación: ejecutar reconciliar para un viaje con documentos faltantes y verificar que el badge se actualiza (reload automático) y que las URLs de documentos aparecen en el modal.

**Cómo probar localmente:**
1. Levantar la app: `ng serve` (o usar su configuración habitual).
2. Abrir `/admin/documents-generated` y/o `/operator/documents-generated`.
3. Revisar badges X/3 en la tabla. Click en "Ver Documentos" para inspeccionar.
4. Pulsar "Reconcilier/Generar" (o la acción correspondiente) para generar documentos faltantes; esperar actualización de la fila.

**Notas y siguientes pasos sugeridos:**
- Se añadió un pequeño ajuste visual con `ChangeDetectorRef` para forzar refresco cuando la reconciliación concluía; esto evitó un parpadeo en la tabla durante pruebas manuales.
- Si desea, puedo:
  - Ejecutar la suite de tests (`ng test`) y corregir fallos que aparezcan.
  - Hacer un commit con un mensaje sugerido y crear una rama/PR.

**Ubicación del informe:**
- Archivo guardado en la raíz del proyecto: [task-11-report.md](task-11-report.md)

Fecha: 2026-05-21
