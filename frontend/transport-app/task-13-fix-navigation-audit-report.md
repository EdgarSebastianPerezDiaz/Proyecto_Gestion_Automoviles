Reporte final: Fix navegación Users + carga inicial de Auditoría

Resumen
- Se corrigió la navegación del enlace "Usuarios y Roles" para que cargue el módulo `/admin/users`.
- Se reforzó la carga inicial del módulo de Auditoría para que la tabla muestre datos al entrar a `/admin/audit` sin necesidad de aplicar filtros.
- La compilación de desarrollo finalizó correctamente, y la verificación en navegador confirmó que el error NG6001 ya no bloquea el módulo.

Cambios realizados

1) Ruta lazy de Usuarios
- Archivo: `src/app/features/admin/admin/admin-routing.module.ts`
- Cambio: Se agregó la ruta lazy loading de usuarios:

```ts
{ path: 'users', loadChildren: () => import('../users/users.module').then(m => m.UsersModule) }
```

- Resultado: al hacer clic en "Usuarios y Roles", Angular carga `UsersModule` en lugar de quedarse en el dashboard.
- Verificación manual en navegador:
  - URL resultante: `http://localhost:4200/admin/users`
  - Resultado visible: 3 filas mock cargadas (`USR-001`, `USR-002`, `USR-003`).

2) Carga inicial de Auditoría
- Archivo: `src/app/features/admin/audit/audit/audit.component.ts`
- Cambios:
  - `ngOnInit()` llama a `loadOperations()` y `loadLogins()`.
  - Se inyectó `ChangeDetectorRef`.
  - Después de asignar `operations`, `totalOperations`, `logins` y `totalLogins`, se llama a `this.cdr.detectChanges()`.
  - Se agregaron logs de depuración:
    - `Cargando operaciones...`
    - `Operaciones recibidas: ...`
    - `Cargando logins...`
    - `Logins recibidos: ...`
- Verificación manual en navegador:
  - URL resultante: `http://localhost:4200/admin/audit`
  - Resultado visible: la tabla muestra filas al cargar y el contador indica `Mostrando 1 - 10 de 37 registros`.
  - Logs observados en consola:
    - `Cargando operaciones...`
    - `Cargando logins...`
    - `Operaciones recibidas: [Object, Object, ...]`
    - `Logins recibidos: [Object, Object, ...]`

3) Verificación del servicio mock
- Archivo: `src/app/core/services/audit.service.ts`
- Resultado: el servicio mock ya devuelve datos para operaciones y logins desde el inicio, incluyendo el caso `actionFilter = 'todos'`.

4) Verificación de UsersModule
- Archivos revisados:
  - `src/app/features/admin/users/users.module.ts`
  - `src/app/features/admin/users/users-routing.module.ts`
  - `src/app/features/admin/users/users/users.component.ts`
- Resultado:
  - `UsersComponent` está exportado y declarado.
  - `UsersModule` importa `CommonModule`, `SharedModule` y `UsersRoutingModule`.
  - La ruta por defecto carga `UsersComponent`.
  - No se detectó `standalone: true` accidental.

Evidencia de compilación
- Comando ejecutado:

```bash
cd frontend/transport-app
ng build --configuration=development
```

- Resultado: compilación exitosa.
- Observación: el build completó sin NG6001, y el bundle incluye `users-module` y `audit-module`.

Evidencia de navegador
- `/admin/users`
  - Sidebar navega correctamente desde el dashboard.
  - Se muestran 3 usuarios mock.
- `/admin/audit`
  - La tabla no queda vacía al entrar.
  - Las filas aparecen sin necesidad de filtrar.

Pruebas manuales sugeridas
1. Inicia sesión como admin.
2. Haz clic en "Usuarios y Roles".
   - Debe navegar a `/admin/users` y mostrar el listado mock.
3. Entra a `/admin/audit`.
   - La tabla debe mostrar registros inmediatamente al cargar la página.
4. Abre la consola (F12) si quieres validar los logs de depuración.

Resultado esperado en consola al abrir auditoría
- `Cargando operaciones...`
- `Operaciones recibidas: [...]`
- `Cargando logins...`
- `Logins recibidos: [...]`

Conclusión
- La navegación de usuarios quedó registrada correctamente.
- La auditoría carga datos al inicio.
- La compilación de desarrollo pasó con éxito, por lo que el error NG6001 no se reproduce en la verificación actual.
- La navegación y la tabla de auditoría quedaron validadas manualmente en el navegador.

