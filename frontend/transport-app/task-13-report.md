Reporte: Implementación Módulo Usuarios y Roles (Task 13)

Resumen
- Alcance: Implementación de un módulo de gestión de usuarios y roles (solo administración) con datos mock, componentes y rutas protegidas. No se implementó backend real; todo es mock en el frontend.

Archivos creados
- `src/app/core/services/user.service.ts` — Servicio mock de usuarios con métodos: `getUsers`, `getUserById`, `createUser`, `updateUser`, `deleteUser`, `getAdminPrincipal`.
- `src/app/features/admin/users/users.module.ts` — Módulo de usuarios.
- `src/app/features/admin/users/users-routing.module.ts` — Rutas del módulo (`/admin/users`).
- `src/app/features/admin/users/users/users.component.ts` — Componente principal (listado, paginación, filtros, acciones).
- `src/app/features/admin/users/users/users.component.html` — Template del listado.
- `src/app/features/admin/users/users/users.component.css` — Estilos mínimos del listado.
- `src/app/shared/components/user-form-modal/user-form-modal.component.ts` — Componente modal para crear/editar usuarios (reactive form y validaciones mínimas).
- `src/app/shared/components/user-form-modal/user-form-modal.component.html` — Template del modal.
- `src/app/shared/components/user-form-modal/user-form-modal.component.css` — Estilos del modal.
- `src/app/task-13-report.md` — Este reporte (ubicado en la raíz del frontend: `frontend/transport-app/task-13-report.md`).

Modificaciones realizadas
- `src/app/shared/shared.module.ts` — Registrado y exportado `UserFormModalComponent`.
- `src/app/shared/components/sidebar/sidebar.component.ts` — Asegurada existencia de la entrada `Usuarios y Roles` (path `/admin/users`). Si ya existía, no se añadió duplicado.

Datos mock incluidos
- Usuarios iniciales cargados en `UserService`:
  - `USR-001` – Juan García — rol: `administrador` — último acceso: `2026-03-11T18:03:00` — NO ELIMINABLE.
  - `USR-002` – Carlos Pérez — rol: `operario` — último acceso: `2026-03-11T07:58:00`.
  - `USR-003` – María Suárez — rol: `operario` — último acceso: `2026-03-09T14:22:00`.
- Creación de nuevos usuarios: IDs secuenciales `USR-004`, `USR-005`, etc. Contraseña almacenada solo de forma mock en memoria (campo `_mockPassword`).

Comandos ejecutados (en el entorno del proyecto)
- Compilar para verificar integridad:

```bash
cd frontend/transport-app
ng build --configuration=development
```

- Iniciar servidor de desarrollo (opcional para pruebas manuales):

```bash
cd frontend/transport-app
ng serve --host 127.0.0.1 --port 4200
```

Evidencia de build
- `ng build --configuration=development` completó correctamente (generó `dist/transport-app`). Esto indica que los nuevos archivos y cambios no introdujeron errores de compilación.

Pasos de prueba manuales (evidencia funcional esperada)
1. Preparación
   - Asegurar que el backend de desarrollo esté corriendo si la app depende de él (no es necesario para el módulo de usuarios mock). Si corresponde:
     ```bash
     cd backend
     python dev_server.py
     ```
   - Iniciar el frontend:
     ```bash
     cd frontend/transport-app
     ng serve
     ```
2. Iniciar sesión como administrador.
3. Navegar a `/admin/users`.
4. Verificar que aparecen los 3 usuarios mock listados: `USR-001`, `USR-002`, `USR-003`.
5. Verificar alerta superior: “⚠️ El Administrador principal (USR-001) no puede ser eliminado del sistema.”
6. Buscar por nombre: escribir "Carlos" en la búsqueda → la lista debe filtrar y mostrar `USR-002`.
7. Filtrar por rol: pulsar "Operario" → la tabla muestra solo operarios.
8. Crear usuario:
   - Pulsar "+ Crear Usuario" → se abre modal.
   - Completar `nombre`, `email`, `password` y `confirmPassword` (mínimo 6 chars). Rol por defecto `operario`.
   - Guardar → modal cierra y el nuevo usuario aparece con ID `USR-004`.
9. Editar usuario operario:
   - Pulsar ✏️ en la fila → modal de edición.
   - Cambiar `nombre` o `email` → Guardar → tabla refleja cambios.
10. Intentar eliminar `USR-001`:
    - El botón eliminar debe estar deshabilitado o al pulsarlo debe mostrar advertencia y no eliminar.
11. Eliminar otro usuario operario:
    - Pulsar 🗑️ en la fila (confirmar) → usuario eliminado de la tabla.
12. Probar acceso por rol:
    - Cerrar sesión y entrar como operador → navegar a `/admin/users` debe redirigir o negar acceso (comportamiento tiene que gobernarse por `roleGuard` ya presente en la app).

Limitaciones y notas
- El módulo usa datos mock en `UserService`; la creación/edición/eliminación no persisten fuera de la sesión actual del frontend.
- No se permitió crear administradores desde el modal (creación asigna rol `operario` siempre).
- En edición no se permite cambiar el rol (evita crear múltiples admins por el flujo mock).
- Validaciones: nombre mínimo 3 caracteres, email válido; contraseña mínimo 6 caracteres y confirmación igual (solo en creación).
- Comprobación de email único: implementada como verificación en `UserService.createUser()` y lanzará error si el email ya existe.

Archivos y rutas exactas (resumen)
- `src/app/core/services/user.service.ts`
- `src/app/features/admin/users/users.module.ts`
- `src/app/features/admin/users/users-routing.module.ts`
- `src/app/features/admin/users/users/users.component.ts`
- `src/app/features/admin/users/users/users.component.html`
- `src/app/features/admin/users/users/users.component.css`
- `src/app/shared/components/user-form-modal/user-form-modal.component.ts`
- `src/app/shared/components/user-form-modal/user-form-modal.component.html`
- `src/app/shared/components/user-form-modal/user-form-modal.component.css`
- `src/app/shared/shared.module.ts` (modificado para exportar el modal)

Fin del reporte.
