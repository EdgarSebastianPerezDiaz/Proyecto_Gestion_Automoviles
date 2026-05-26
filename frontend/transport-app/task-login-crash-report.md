Reporte: Login congelado / crash diagnóstico y correcciones

Resumen
- Síntoma: El botón de login quedaba deshabilitado mostrando "Ingresando..." y la petición HTTP no completaba (estado pendiente) hasta que el usuario interactuaba con la página, momento en el cual aparecía "credenciales inválidas".
- Causa principal detectada: Backend de desarrollo (`http://localhost:5000`) no estaba corriendo — las peticiones quedaban en pending. Una vez levantado el servidor, el login respondió correctamente.

Acciones aplicadas (por orden solicitado)

1) Verificar backend /health
- Verificado: `http://localhost:5000/health` respondió `{"message":"ok"}` tras ejecutar `python dev_server.py`.

2) Inspección Network
- Resultado reportado por el usuario: al arrancar el backend la petición a `/api/auth/login` deja de quedar en `pending` y responde.

3) Interceptor (`src/app/core/auth/auth.interceptor.ts`)
- Cambio: Añadida protección para no intentar refresh cuando la petición fallida es `/auth/login` (evita bucles de refresh).
- No se deshabilitó por completo el refresh; solo se evitó el intento en el caso del login.

4) `AuthService.login` (`src/app/core/auth/auth.service.ts`)
- Cambio: Se añadió `console.log` al resolver el `login()` para trazar el usuario y tokens almacenados.

5) `LoginComponent` (`src/app/features/auth/login.component.ts`)
- Cambio: Añadido `console.log` en el `subscribe` de `onSubmit()` para facilitar inspección de la respuesta en la consola.

6) Dashboard operador
- `src/app/core/services/dashboard.service.ts`: `getOperatorDashboard()` ahora emite con `delay(300)` para simular latencia y evitar condiciones de carrera.
- `src/app/features/operator/dashboard/dashboard.component.ts`: Reemplazado `forkJoin` por suscripciones independientes y añadido `ChangeDetectorRef.detectChanges()` después de asignar datos para forzar renderizado.

Resultados
- Con el backend levantado, el login funciona correctamente y redirige por rol.
- Las modificaciones añadieron trazas en consola para depuración y mitigaron un posible bucle de refresh en el interceptor.

Recomendaciones siguientes
- Revisar/rehabilitar cuidadosamente la lógica de refresh automática: probar escenarios de expiración de token y multi-peticiones concurrentes para garantizar que `refreshToken()` se ejecute exactamente cuando corresponde.
- Añadir logs más explícitos en el interceptor (o usar un logger) para detectar retransmisiones y refreshes en entorno de QA.
- (Opcional) Implementar tests E2E que simulen token expirado y validen el flujo de refresh.

Instrucciones rápidas para reproducir localmente
1. Iniciar backend:

```bash
cd backend
python dev_server.py
```

2. Iniciar frontend (si no está corriendo):

```bash
cd frontend/transport-app
npm install
ng serve
```

3. Abrir http://localhost:4200/login, abrir DevTools → Network, hacer login con credenciales de prueba y verificar que la petición a `/api/auth/login` retorna y la UI redirige.

Archivos modificados
- `src/app/core/auth/auth.interceptor.ts`
- `src/app/core/auth/auth.service.ts`
- `src/app/features/auth/login.component.ts`
- `src/app/core/services/dashboard.service.ts`
- `src/app/features/operator/dashboard/dashboard.component.ts`

Si quieres, puedo:
- Comentar temporalmente la lógica de refresh para probar si el interceptor es la fuente del problema (paso 3 original),
- Añadir el header `Content-Type: application/json` explícitamente en `AuthService.login` (paso 4),
- Implementar el mock temporal en `LoginComponent` para aislar el problema (paso 5),
- O ejecutar `ng build --configuration=development` y compartir el resultado.

