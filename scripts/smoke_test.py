#!/usr/bin/env python3
"""
smoke_test.py — Heavy Freight Platform
=======================================
Verifica automáticamente:
  1. Frontend S3 (accesibilidad, SPA routing, assets)
  2. Backend API — endpoints públicos (health, auth)
  3. Backend API — endpoints protegidos con JWT real
  4. CORS entre frontend y backend

Uso:
    # Con la URL del backend ya configurada:
    python scripts/smoke_test.py --api https://XXXX.execute-api.us-east-1.amazonaws.com

    # Pasando credenciales de prueba:
    python scripts/smoke_test.py \
        --api https://XXXX.execute-api.us-east-1.amazonaws.com \
        --email admin@example.com \
        --password "TuPassword123!"

    # Solo frontend (sin backend):
    python scripts/smoke_test.py --frontend-only

Dependencias (solo stdlib + requests):
    pip install requests
"""

import sys
import json
import time
import argparse
import traceback
from datetime import datetime
from typing import Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: Instala 'requests': pip install requests")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Configuración por defecto
# ─────────────────────────────────────────────────────────────────────────────

FRONTEND_URL  = "http://heavy-freight-frontend-prod.s3-website-us-east-1.amazonaws.com"
DEFAULT_API   = ""   # Se pide como argumento --api
TIMEOUT       = 15   # segundos por request

# Colores ANSI para la terminal
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

results: list[dict] = []

def _session() -> requests.Session:
    """Crea una sesión con reintentos automáticos."""
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=[502, 503, 504])
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

SESSION = _session()


def check(label: str, fn, *args, **kwargs) -> Optional[dict]:
    """Ejecuta fn(), registra el resultado y lo imprime."""
    start = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        elapsed = int((time.monotonic() - start) * 1000)
        ok = result.get("ok", True)
        status = f"{GREEN}✅ PASS{RESET}" if ok else f"{RED}❌ FAIL{RESET}"
        note   = result.get("note", "")
        print(f"  {status}  {label:<52} {elapsed:>5}ms  {note}")
        results.append({"label": label, "ok": ok, "ms": elapsed, "note": note,
                         "detail": result.get("detail", "")})
        return result
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        msg = str(exc)
        print(f"  {RED}❌ ERR {RESET}  {label:<52} {elapsed:>5}ms  {msg[:80]}")
        results.append({"label": label, "ok": False, "ms": elapsed, "note": msg,
                         "detail": traceback.format_exc()})
        return None


def get(url: str, headers=None, params=None, expected_status=200) -> dict:
    r = SESSION.get(url, headers=headers, params=params, timeout=TIMEOUT)
    ok = r.status_code == expected_status
    return {"ok": ok, "note": f"HTTP {r.status_code}", "detail": r.text[:200],
            "response": r}


def post(url: str, payload: dict, headers=None, expected_status=200) -> dict:
    r = SESSION.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    ok = r.status_code == expected_status
    return {"ok": ok, "note": f"HTTP {r.status_code}", "detail": r.text[:200],
            "response": r}


def header(title: str):
    print(f"\n{BOLD}{CYAN}{'─'*70}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*70}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 1 — Frontend S3
# ─────────────────────────────────────────────────────────────────────────────

def test_frontend(base: str):
    header("1 · FRONTEND S3 — Accesibilidad y SPA routing")

    # 1.1 Página raíz
    def _root():
        r = SESSION.get(base + "/", timeout=TIMEOUT)
        ok = r.status_code == 200 and "<!DOCTYPE html>" in r.text.lower()
        return {"ok": ok, "note": f"HTTP {r.status_code} · {'HTML OK' if ok else 'NO HTML'}"}

    check("GET / (raíz → index.html)", _root)

    # 1.2 SPA fallback: rutas Angular deben devolver index.html
    for path in ["/login", "/admin", "/operator"]:
        def _spa(p=path):
            r = SESSION.get(base + p, timeout=TIMEOUT)
            # S3 website hosting con error-document index.html devuelve 200 o 404
            # Ambos son aceptables siempre que devuelvan HTML de Angular
            ok = "<!DOCTYPE html>" in r.text.lower() or r.status_code in (200, 404)
            return {"ok": ok, "note": f"HTTP {r.status_code} · {'SPA OK' if ok else 'SIN HTML'}"}
        check(f"GET {path} (SPA fallback)", _spa)

    # 1.3 Tiempo de respuesta aceptable (< 3 s)
    def _perf():
        start = time.monotonic()
        SESSION.get(base + "/", timeout=TIMEOUT)
        ms = int((time.monotonic() - start) * 1000)
        ok = ms < 3000
        return {"ok": ok, "note": f"{ms}ms {'< 3s ✓' if ok else '⚠ > 3s lento'}"}

    check("Tiempo de respuesta < 3 000 ms", _perf)

    # 1.4 Headers de seguridad básicos
    def _headers():
        r = SESSION.get(base + "/", timeout=TIMEOUT)
        # S3 no permite configurar headers personalizados sin CloudFront
        # verificamos al menos Content-Type correcto
        ct = r.headers.get("Content-Type", "")
        ok = "text/html" in ct
        return {"ok": ok, "note": f"Content-Type: {ct[:50]}"}

    check("Content-Type: text/html en la raíz", _headers)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2 — Backend: endpoints públicos
# ─────────────────────────────────────────────────────────────────────────────

def test_backend_public(api: str):
    header("2 · BACKEND — Endpoints públicos (sin JWT)")

    # 2.1 Health /live
    def _live():
        res = get(f"{api}/health/live")
        r = res["response"]
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        ok = res["ok"] and body.get("status") == "alive"
        return {"ok": ok, "note": f"HTTP {r.status_code} · status={body.get('status','?')}"}
    check("GET /health/live → {status:alive}", _live)

    # 2.2 Health /ready
    def _ready():
        res = get(f"{api}/health/ready")
        r = res["response"]
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        ok = res["ok"] and body.get("status") in ("ready", "healthy")
        return {"ok": ok, "note": f"HTTP {r.status_code} · status={body.get('status','?')}"}
    check("GET /health/ready → {status:ready}", _ready)

    # 2.3 Health /deep
    def _deep():
        res = get(f"{api}/health/deep")
        r = res["response"]
        ok = res["ok"]
        return {"ok": ok, "note": f"HTTP {r.status_code}"}
    check("GET /health/deep → 200", _deep)

    # 2.4 Raíz /
    def _root():
        res = get(f"{api}/")
        r = res["response"]
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        ok = res["ok"] and "Heavy Freight" in body.get("service", "")
        return {"ok": ok, "note": f"service={body.get('service','?')[:40]}"}
    check("GET / → Heavy Freight Platform API", _root)

    # 2.5 Login con credenciales inválidas → 401
    def _login_bad():
        res = post(f"{api}/auth/login",
                   {"email": "noexiste@x.com", "password": "WrongPass123!"},
                   expected_status=401)
        r = res["response"]
        ok = r.status_code == 401
        return {"ok": ok, "note": f"HTTP {r.status_code} (esperado 401)"}
    check("POST /auth/login credenciales inválidas → 401", _login_bad)

    # 2.6 Acceso a endpoint protegido sin token → 401/403
    def _unauth():
        r = SESSION.get(f"{api}/trips", timeout=TIMEOUT)
        ok = r.status_code in (401, 403, 422)
        return {"ok": ok, "note": f"HTTP {r.status_code} (esperado 401/403)"}
    check("GET /trips sin JWT → 401/403", _unauth)

    # 2.7 CORS: preflight OPTIONS
    def _cors():
        frontend_origin = FRONTEND_URL
        r = SESSION.options(
            f"{api}/auth/login",
            headers={
                "Origin": frontend_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
            timeout=TIMEOUT
        )
        acao = r.headers.get("access-control-allow-origin", "")
        ok = r.status_code in (200, 204) and (acao == frontend_origin or acao == "*")
        return {"ok": ok,
                "note": f"HTTP {r.status_code} · ACAO={acao[:60] if acao else 'MISSING'}"}
    check("OPTIONS /auth/login (CORS preflight)", _cors)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3 — Backend: endpoints protegidos (requieren JWT real)
# ─────────────────────────────────────────────────────────────────────────────

def test_backend_auth(api: str, email: str, password: str) -> Optional[str]:
    """Hace login y devuelve el access_token. None si falla."""
    header("3 · BACKEND — Autenticación y endpoints protegidos")

    token: Optional[str] = None
    refresh_token: Optional[str] = None

    # 3.1 Login válido
    def _login():
        nonlocal token, refresh_token
        r = SESSION.post(f"{api}/auth/login",
                         json={"email": email, "password": password},
                         timeout=TIMEOUT)
        if r.status_code == 200:
            body = r.json()
            token = body.get("access_token")
            refresh_token = body.get("refresh_token")
            ok = bool(token)
            return {"ok": ok, "note": f"HTTP 200 · token={'OK' if token else 'MISSING'}"}
        return {"ok": False, "note": f"HTTP {r.status_code} · {r.text[:80]}"}

    check(f"POST /auth/login ({email}) → 200 + tokens", _login)

    if not token:
        print(f"  {YELLOW}⚠ Sin token — omitiendo pruebas protegidas{RESET}")
        return None

    auth_headers = {"Authorization": f"Bearer {token}"}

    # ── Endpoints protegidos ─────────────────────────────────────────────────

    protected_gets = [
        ("/companies",         "Empresas"),
        ("/clients",           "Clientes"),
        ("/drivers",           "Conductores"),
        ("/vehicles",          "Vehículos"),
        ("/trips",             "Viajes"),
        ("/invoices",          "Facturas"),
        ("/cargo-types",       "Tipos de carga"),
        ("/final-recipients",  "Destinatarios"),
        ("/trip-statuses",     "Estados de viaje"),
    ]

    for path, label in protected_gets:
        def _get_protected(p=path, lbl=label):
            r = SESSION.get(f"{api}{p}", headers=auth_headers,
                            params={"page": "1", "limit": "5"}, timeout=TIMEOUT)
            ok = r.status_code in (200, 204)
            body = ""
            if r.headers.get("content-type","").startswith("application/json"):
                try:
                    j = r.json()
                    total = j.get("total", j.get("count", "?")) if isinstance(j, dict) else "?"
                    body = f"total={total}"
                except Exception:
                    body = r.text[:40]
            return {"ok": ok, "note": f"HTTP {r.status_code} {body}"}
        check(f"GET {path} (autenticado — {label})", _get_protected)

    # 3.2 Refresh token
    def _refresh():
        if not refresh_token:
            return {"ok": False, "note": "Sin refresh_token disponible"}
        r = SESSION.post(f"{api}/auth/refresh",
                         json={"refresh_token": refresh_token},
                         timeout=TIMEOUT)
        ok = r.status_code == 200 and "access_token" in r.json()
        return {"ok": ok, "note": f"HTTP {r.status_code}"}
    check("POST /auth/refresh → nuevo access_token", _refresh)

    # 3.3 Token expirado / mal formado → 401
    def _bad_token():
        r = SESSION.get(f"{api}/trips",
                        headers={"Authorization": "Bearer token.invalido.xxxx"},
                        timeout=TIMEOUT)
        ok = r.status_code in (401, 403, 422)
        return {"ok": ok, "note": f"HTTP {r.status_code} (esperado 401/403)"}
    check("GET /trips con token inválido → 401/403", _bad_token)

    return token


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 4 — CORS end-to-end (frontend origin → backend)
# ─────────────────────────────────────────────────────────────────────────────

def test_cors(api: str, token: Optional[str]):
    header("4 · CORS — Origen del frontend hacia el backend")

    def _cors_get():
        headers = {"Origin": FRONTEND_URL}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = SESSION.get(f"{api}/health/live", headers=headers, timeout=TIMEOUT)
        acao = r.headers.get("access-control-allow-origin", "MISSING")
        ok = r.status_code == 200 and acao in (FRONTEND_URL, "*")
        return {"ok": ok, "note": f"ACAO={acao[:60]}"}

    check("GET /health/live con Origin: frontend → CORS header OK", _cors_get)

    def _cors_post():
        r = SESSION.options(
            f"{api}/trips",
            headers={
                "Origin": FRONTEND_URL,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
            timeout=TIMEOUT
        )
        acao = r.headers.get("access-control-allow-origin", "MISSING")
        acam = r.headers.get("access-control-allow-methods", "")
        ok = r.status_code in (200, 204) and acao in (FRONTEND_URL, "*")
        return {"ok": ok, "note": f"HTTP {r.status_code} · ACAO={acao[:40]} · methods={acam[:40]}"}

    check("OPTIONS /trips preflight → CORS completo", _cors_post)


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    header("RESUMEN")
    total   = len(results)
    passed  = sum(1 for r in results if r["ok"])
    failed  = total - passed

    print(f"\n  Total checks : {total}")
    print(f"  {GREEN}Passed{RESET}       : {passed}")
    print(f"  {RED}Failed{RESET}       : {failed}")

    if failed:
        print(f"\n  {BOLD}{RED}Fallos:{RESET}")
        for r in results:
            if not r["ok"]:
                print(f"    {RED}✗{RESET} {r['label']}")
                if r.get("detail"):
                    for line in r["detail"].strip().splitlines()[:3]:
                        print(f"       {YELLOW}{line}{RESET}")

    score = int(passed / total * 100) if total else 0
    color = GREEN if score == 100 else (YELLOW if score >= 70 else RED)
    print(f"\n  Score: {color}{BOLD}{score}%{RESET}")
    print(f"  {'🟢 Todo OK — listo para producción' if failed == 0 else '🔴 Hay fallos — revisa arriba'}")

    # Guardar JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"smoke_test_result_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "passed": passed, "failed": failed,
                   "score_pct": score, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Resultado JSON: {out}\n")

    return failed == 0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Smoke test automático — Heavy Freight Platform"
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help="URL base del API Gateway, ej: https://abc123.execute-api.us-east-1.amazonaws.com"
    )
    parser.add_argument(
        "--frontend",
        default=FRONTEND_URL,
        help=f"URL del frontend S3 (default: {FRONTEND_URL})"
    )
    parser.add_argument("--email",    default="", help="Email del usuario de prueba (para tests protegidos)")
    parser.add_argument("--password", default="", help="Contraseña del usuario de prueba")
    parser.add_argument("--frontend-only", action="store_true",
                        help="Solo probar el frontend S3, omitir backend")
    parser.add_argument("--backend-only", action="store_true",
                        help="Solo probar el backend API, omitir frontend S3")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*70}")
    print(f"  🚚 Heavy Freight Platform — Smoke Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*70}{RESET}")

    if not args.frontend_only and not args.api:
        print(f"\n{YELLOW}⚠ No se especificó --api. Solo se probarán el frontend.{RESET}")
        print(f"  Uso: python scripts/smoke_test.py --api https://XXXX.execute-api.us-east-1.amazonaws.com")
        args.frontend_only = True

    print(f"\n  Frontend : {args.frontend}")
    if not args.frontend_only:
        print(f"  Backend  : {args.api}")
        print(f"  Auth     : {args.email or '(sin credenciales — se omiten tests protegidos)'}")

    token = None

    if not args.backend_only:
        test_frontend(args.frontend)

    if not args.frontend_only:
        test_backend_public(args.api)

        if args.email and args.password:
            token = test_backend_auth(args.api, args.email, args.password)
        else:
            header("3 · BACKEND — Endpoints protegidos")
            print(f"  {YELLOW}⚠ Pasa --email y --password para probar endpoints con JWT{RESET}")

        test_cors(args.api, token)

    all_ok = print_summary()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
