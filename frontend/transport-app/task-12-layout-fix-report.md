Reporte: Corrección de layout del Módulo Auditoría

Resumen
- Problema: El módulo de Auditoría mostraba su contenido pero no incluía el `app-navbar` ni el `app-sidebar`, impidiendo la navegación y dejando la interfaz incompleta.
- Objetivo: Ajustar `AuditComponent` para que use el mismo layout que los demás módulos: `app-navbar` en la parte superior, `app-sidebar` a la izquierda y el contenido dentro de un `main` con `flex-1`.

Cambios aplicados
1) Plantilla
- Archivo modificado: `src/app/features/admin/audit/audit/audit.component.html`
- Acción: Reempaqueté TODO el contenido existente dentro de la estructura:

```html
<div class="min-h-screen bg-gray-50">
  <app-navbar></app-navbar>
  <div class="flex">
    <app-sidebar></app-sidebar>
    <main class="flex-1 p-6">
      <!-- Contenido original del componente (pestañas, tablas, filtros, paginación, export) -->
    </main>
  </div>
</div>
```

- Importante: No modifiqué la lógica de datos ni las funciones/handlers — solo moví el HTML existente dentro del `<main>`.

2) Módulo
- Archivo verificado: `src/app/features/admin/audit/audit.module.ts`
- Resultado: `SharedModule` ya estaba importado; no fue necesario cambiar imports.

Verificación
- Compilación: Ejecuté `ng build --configuration=development` y la compilación finalizó correctamente sin errores.
- Ruta probada: `http://localhost:4200/admin/audit` (con servidor de backend y frontend levantados)

Captura de texto de la interfaz después del cambio
- Encabezado superior (navbar):
  TRANSPORTES ABC — Usuario: Admin Test — Logout

- Estructura lateral (sidebar) — elementos visibles (ejemplo):
  - Dashboard
  - Viajes
  - Conductores
  - Vehículos
  - Empresas
  - Auditoría
  - Reportes

- Área principal (`main`) — contenido de Auditoría:
  - Título: "Auditoría"
  - Pestañas: [Operaciones] [Inicios de Sesión]
  - Controles: buscador, filtros por acción, botón "Exportar todo a CSV"
  - Tabla de resultados con columnas: Fecha y Hora | Tabla Afectada | ID Registro | Acción | Usuario Responsable | Exportar
  - Paginación: botones "← Anterior" y "Siguiente →" y contador de registros

Notas adicionales
- No modifiqué estilos globales ni la lógica de los servicios.
- `SharedModule` ya exporta `NavbarComponent` y `SidebarComponent`; por eso la inclusión en la plantilla funcionó sin cambios en el módulo.

Siguientes pasos recomendados
- Prueba manual: iniciar sesión como admin y navegar a `/admin/audit` para confirmar que:
  - Se muestra la barra superior con el nombre del sistema y control de logout.
  - El menú lateral aparece y permite navegar a otras secciones.
  - Las pestañas, filtros, paginación y exportación siguen funcionando.
- Si ves algún problema visual menor, puedo ajustar márgenes/paddings para que el contenido central quede alineado con otros módulos.

Archivos modificados
- `src/app/features/admin/audit/audit/audit.component.html`

Fecha: 2026-05-22
Autor: asistente (copilot)
