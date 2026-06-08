Reporte final: Fix layout del módulo Usuarios y Roles

Resumen
- Se aplicó la misma estructura de layout usada en Auditoría y en el resto de módulos funcionales.
- La página de `/admin/users` ahora muestra `app-navbar` en la parte superior y `app-sidebar` a la izquierda.
- Todo el contenido funcional del listado de usuarios quedó dentro de `<main class="flex-1 p-6">`.

Cambios realizados

1) Template de Usuarios
- Archivo: `src/app/features/admin/users/users/users.component.html`
- Cambio aplicado:
  - Se reemplazó el contenido del template por la estructura:

```html
<div class="min-h-screen bg-gray-50">
  <app-navbar></app-navbar>
  <div class="flex">
    <app-sidebar></app-sidebar>
    <main class="flex-1 p-6">
      <!-- contenido original de usuarios -->
    </main>
  </div>
</div>
```

- El contenido original del componente quedó dentro del `<main>`.
- No se modificó la lógica de datos ni los estilos globales.

2) Módulo de Usuarios
- Archivo verificado: `src/app/features/admin/users/users.module.ts`
- Resultado: `SharedModule` ya estaba importado, por lo que `NavbarComponent` y `SidebarComponent` están disponibles para el template.

Evidencia de compilación
- Comando ejecutado:

```bash
cd frontend/transport-app
ng build --configuration=development
```

- Resultado: compilación exitosa.
- Observación: el bundle del proyecto se generó correctamente y el módulo `users-module` quedó incluido.

Descripción textual de la página después del cambio
- En la parte superior se ve la barra con:
  - `TRANSPORTES ABC`
  - usuario conectado
  - botón `Cerrar sesión`
- A la izquierda aparece el menú lateral completo con opciones administrativas.
- En el área principal se ve:
  - Título `Usuarios y Roles`
  - Buscador por nombre
  - Filtros `Todos`, `Administrador`, `Operario`
  - Mensaje de advertencia sobre el administrador principal no eliminable
  - Tabla de usuarios con acciones editar/eliminar
  - Paginación y modal de creación/edición

Validación manual esperada
1. Iniciar sesión como admin.
2. Ir a `/admin/users`.
3. Confirmar que la interfaz muestra navbar, sidebar y el contenido del listado dentro del panel principal.
4. Verificar que búsqueda, filtros, paginación y botones siguen funcionando.

Conclusión
- El layout de Usuarios y Roles quedó alineado con el resto de la aplicación.
- La estructura común de navegación ya está presente en la vista.
- La compilación de desarrollo pasó correctamente después del ajuste.

