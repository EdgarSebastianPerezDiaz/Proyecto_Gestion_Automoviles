**Informe Tarea 12 — Módulo de Auditoría**

**Objetivo:**
- Implementar el módulo de Auditoría para administradores con pestañas "Operaciones" e "Inicios de Sesión", búsqueda, filtros rápidos, paginación y exportación a CSV.

**Archivos creados/clave:**
- `src/app/core/services/audit.service.ts` — servicio mock con `AuditOperation` y `AuditLogin`, métodos de paginación y exportación.
- `src/app/core/services/export.service.ts` — utilidad para exportar arrays a CSV.
- `src/app/features/admin/audit/audit.module.ts` — módulo lazy del feature.
- `src/app/features/admin/audit/audit-routing.module.ts` — ruta `/admin/audit`.
- `src/app/features/admin/audit/audit/audit.component.ts` — componente principal con pestañas, tablas, filtros, paginación y export.
- `src/app/features/admin/audit/audit/audit.component.html` — template.
- `src/app/features/admin/audit/audit/audit.component.css` — estilos mínimos.
- `task-12-report.md` — este informe.

**Comandos ejecutados / verificación:**
- Archivos añadidos en `frontend/transport-app`.
- Añadida ruta lazy en `src/app/features/admin/admin/admin-routing.module.ts` para cargar el módulo de auditoría.
- Compilación propuesta: `ng build --configuration=development` (ejecutar localmente para verificar en su entorno).

**Cómo probar localmente (resumen):**
1. Levantar la app: `ng serve` desde `frontend/transport-app`.
2. Iniciar sesión como administrador y navegar a `/admin/audit`.
3. Cambiar entre pestañas "Operaciones" e "Inicios de Sesión".
4. Probar búsqueda, filtros rápidos (Operaciones), paginación, exportar todo y exportar fila.
5. Intentar acceder como operador — la ruta está protegida por `roleGuard` en la raíz `/admin`.

**Notas técnicas:**
- Los datos mock están en `AuditService` (30+ operaciones, 20+ logins); métodos usan `of(...).pipe(delay(300))` para simular latencia.
- Exportación genera CSV sin librerías externas (servicio `ExportService`). Fechas formateadas `DD/MM/YYYY HH:MM:SS`.
- Componentes siguen la convención `standalone: false` y están declarados en módulos.

Fecha: 2026-05-21
