Reporte final: Fix layout del módulo de Auditoría

Resumen
- Se aplicó la estructura estándar de la aplicación al módulo de Auditoría.
- La página de `/admin/audit` ahora se renderiza con `app-navbar` en la parte superior y `app-sidebar` a la izquierda.
- Todo el contenido funcional de auditoría quedó dentro de `<main class="flex-1 p-6">`, manteniendo pestañas, filtros, tabla, paginación y exportación.

Cambios realizados

1) Template de Auditoría
- Archivo: `src/app/features/admin/audit/audit/audit.component.html`
- Cambio aplicado:
  - Se reemplazó el contenido del template por la estructura:

```html
<div class="min-h-screen bg-gray-50">
  <app-navbar></app-navbar>
  <div class="flex">
    <app-sidebar></app-sidebar>
    <main class="flex-1 p-6">
      <!-- contenido original de auditoría -->
    </main>
  </div>
</div>
```

- El contenido original del componente quedó dentro del `<main>`.
- No se modificó la lógica de datos ni los estilos globales.

2) Módulo de Auditoría
- Archivo verificado: `src/app/features/admin/audit/audit.module.ts`
- Resultado: `SharedModule` ya estaba importado, por lo que `NavbarComponent` y `SidebarComponent` quedan disponibles para el template.

Evidencia de compilación
- Comando ejecutado:

```bash
cd frontend/transport-app
ng build --configuration=development
```

- Resultado: compilación exitosa.
- Observación: el bundle del proyecto se generó correctamente y el módulo `audit-module` quedó incluido.

Descripción textual de la página después del cambio
- En la parte superior se ve la barra con:
  - `TRANSPORTES ABC`
  - usuario conectado
  - botón `Cerrar sesión`
- A la izquierda aparece el menú lateral completo con opciones administrativas.
- En el área principal se ve:
  - Título `Auditoría`
  - Pestañas `Operaciones` e `Inicios de Sesión`
  - Buscadores, filtros por acción, botón de exportación CSV
  - Tabla con registros de auditoría
  - Controles de paginación

Validación manual esperada
1. Iniciar sesión como admin.
2. Ir a `/admin/audit`.
3. Confirmar que la interfaz muestra navbar, sidebar y el contenido de auditoría dentro del panel principal.
4. Verificar que pestañas, filtros y paginación siguen funcionando.

Conclusión
- El layout de Auditoría quedó alineado con el resto de la aplicación.
- La estructura común de navegación ya está presente en la vista.
- La compilación de desarrollo pasó correctamente después del ajuste.

