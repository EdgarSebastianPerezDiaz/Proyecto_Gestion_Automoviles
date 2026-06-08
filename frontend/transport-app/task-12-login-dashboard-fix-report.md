Resumen de cambios (Login / Logout / Dashboard) - Task 12

Objetivo
- Corregir bloqueo de login tras logout y asegurar carga confiable del Dashboard operador.

Cambios realizados (orden estrictamente seguido)

1) Interceptor de auth
- Archivo: [src/app/core/auth/auth.interceptor.ts](src/app/core/auth/auth.interceptor.ts)
- Acción: Evitar intento de refresh cuando la petición fallida es el endpoint `/auth/login` (previene bucles de refresco). También se preserva la lógica de agregar `Authorization` sólo si hay token válido.

2) Servicio de autenticación
- Archivo: [src/app/core/auth/auth.service.ts](src/app/core/auth/auth.service.ts)
- Acción: Añadido `console.log` en el flujo de `login()` para registrar el usuario y tokens almacenados; se mantiene `catchError` para propagar errores correctamente.

3) Componente de login
- Archivo: [src/app/features/auth/login.component.ts](src/app/features/auth/login.component.ts)
- Acción: Añadido `console.log` en el `subscribe` de `onSubmit()` para inspección explícita de la respuesta y facilitar diagnóstico de bloqueos aparente.

4) Backend / Health-check
- Nota: No se realizaron cambios en el servidor desde el cliente. Si el backend de desarrollo no está levantado, el login fallará con error de red (status 0). Asegurarse de ejecutar el servidor dev (por ejemplo `python backend/dev_server.py` o equivalente) antes de probar.

5) Servicios y Dashboard operador
- Archivo: [src/app/core/services/dashboard.service.ts](src/app/core/services/dashboard.service.ts)
- Acción: `getOperatorDashboard()` ahora emite con `delay(300)` para simular latencia y evitar condiciones de carrera en la UI.

- Archivo: [src/app/features/operator/dashboard/dashboard.component.ts](src/app/features/operator/dashboard/dashboard.component.ts)
- Acción: Reemplazado `forkJoin` por suscripciones independientes a `getOperatorDashboard()` y `getActiveTrips()`; inyectado `ChangeDetectorRef` y llamado `detectChanges()` después de cada asignación para forzar renderizado inmediato y evitar que la UI requiera una interacción del usuario para refrescar.

Verificación recomendada (pasos manuales)

1. Preparación
- Asegúrate de tener el backend de desarrollo corriendo (por ejemplo `http://localhost:5000`), si aplica.
- Borra el estado previo: abre la consola del navegador y ejecuta `localStorage.clear()`.

2. Flujo de login
- Navega a `/login`.
- Ingresa credenciales de prueba (p. ej. `admin@test.com` / `password123` o `operator@test.com` / `password123`).
- Observa la consola del navegador: deberías ver los `console.log` desde `LoginComponent` y `AuthService` mostrando la respuesta y el usuario almacenado.
- Verifica que la navegación redirige correctamente según rol a `/admin/dashboard` o `/operator/dashboard`.

3. Logout y re-login
- Haz logout desde la UI.
- Confirma que `localStorage` quedó vacío y que la app navegó a `/login`.
- Intenta login nuevamente; la petición no debería quedar colgada ni intentar refrescar tokens para la ruta `/auth/login`.

4. Dashboard operador
- Ingresa con un usuario operador.
- Verifica que los KPIs, alertas y lista de viajes se muestren sin necesitar clicks adicionales.
- Si hay problemas, revisa la consola para errores; las suscripciones independientes y `detectChanges()` deberían evitar que la UI se quede sin renderizar.

Archivos modificados
- [src/app/core/auth/auth.interceptor.ts](src/app/core/auth/auth.interceptor.ts)
- [src/app/core/auth/auth.service.ts](src/app/core/auth/auth.service.ts)
- [src/app/features/auth/login.component.ts](src/app/features/auth/login.component.ts)
- [src/app/core/services/dashboard.service.ts](src/app/core/services/dashboard.service.ts)
- [src/app/features/operator/dashboard/dashboard.component.ts](src/app/features/operator/dashboard/dashboard.component.ts)

Siguientes pasos sugeridos
- Ejecutar `ng build --configuration=development` o iniciar la app y realizar la verificación manual descrita.
- Si persiste bloqueo en login tras logout, proporcionar los logs de red (Network) y consola para diagnóstico adicional.

Registro de cambios breve
- Fecha: (hoy)
- Autor: GitHub Copilot (GPT-5 mini)

