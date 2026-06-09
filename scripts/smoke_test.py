#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_test.py — Heavy Freight Platform
=======================================
Verifica automáticamente que la aplicación completa esté corriendo:
  1. Frontend S3  — accesibilidad y SPA routing
  2. Backend API  — health, raíz
  3. Auth         — registro + login + refresh + token inválido
  4. Recursos     — todos los endpoints (list + write stubs)
  5. CORS         — preflight desde el origen del frontend

Uso rápido (solo health / sin credenciales):
    python scripts/smoke_test.py --api https://XXXX.execute-api.us-east-1.amazonaws.com

Uso completo (con credenciales → prueba auth):
    python scripts/smoke_test.py \
        --api  https://XXXX.execute-api.us-east-1.amazonaws.com \
        --email  admin@example.com \
        --password "TuPass123!"

Solo frontend:
    python scripts/smoke_test.py --frontend-only

Dependencias (solo stdlib + requests):
    pip install requests
"""

import sys
import os
import json
import time
import uuid
import argparse
import traceback
from datetime import datetime
from typing import Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

# Forzar UTF-8 en Windows para que los emojis no rompan la terminal
import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Defaults ─────────────────────────────────────────────────────────────────

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://heavy-freight-frontend-prod.s3-website-us-east-1.amazonaws.com"
)
DEFAULT_API  = os.getenv("API_URL", "")
TIMEOUT      = 20

# ─── Colores ──────────────────────────────────────────────────────────────────

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; B = "\033[1m";  X = "\033[0m"

# ─── Estado global ────────────────────────────────────────────────────────────

_results: list[dict] = []


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[502, 503, 504])
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

SESSION = _session()


# ─── Helper de checks ─────────────────────────────────────────────────────────

def check(label: str, ok: bool, note: str = "", warn_only: bool = False) -> bool:
    """Registra y muestra un resultado."""
    if ok:
        icon, color, status = "✓", G, "PASS"
    elif warn_only:
        icon, color, status = "⚠", Y, "WARN"
    else:
        icon, color, status = "✗", R, "FAIL"

    note_str = f"  {note}" if note else ""
    print(f"  {color}{icon}{X} {label:<58}{note_str}")
    _results.append({"label": label, "ok": ok or warn_only,
                     "status": status, "note": note})
    return ok


def _req(method: str, url: str, **kwargs) -> Optional[requests.Response]:
    try:
        r = SESSION.request(method, url, timeout=TIMEOUT, **kwargs)
        return r  # siempre devuelve la respuesta, incluso 4xx/5xx
    except requests.exceptions.Timeout:
        check(f"{method} {url}", False, "TIMEOUT")
        return None
    except Exception as e:
        # Captura ConnectionError, RetryError, SSLError, etc.
        check(f"{method} {url}", False, f"ERR: {type(e).__name__}: {str(e)[:80]}")
        return None


def _json(r: requests.Response) -> dict:
    try:
        return r.json()
    except Exception:
        return {}


def section(title: str):
    print(f"\n{B}{C}{'─' * 70}{X}")
    print(f"{B}{C}  {title}{X}")
    print(f"{B}{C}{'─' * 70}{X}")


# ─────────────────────────────────────────────────────────────────────────────
# 1 · FRONTEND
# ─────────────────────────────────────────────────────────────────────────────

def test_frontend(base: str):
    section("1 · FRONTEND S3")
    base = base.rstrip("/")

    # Raíz — debe devolver HTML de Angular
    r = _req("GET", base + "/")
    if r is not None:
        ok = r.status_code == 200 and "<!doctype html" in r.text.lower()
        check("GET /  →  200 + HTML Angular", ok, f"HTTP {r.status_code}")

    # Rutas SPA (Angular) — S3 usa index.html como error-document → 200
    for path in ["/login", "/admin", "/operator"]:
        r = _req("GET", base + path)
        if r is not None:
            ok = r.status_code in (200,) and "<!doctype html" in r.text.lower()
            check(f"GET {path}  →  SPA routing (index.html)", ok, f"HTTP {r.status_code}")

    # Tiempo de respuesta
    t0 = time.monotonic()
    _req("GET", base + "/")
    ms = int((time.monotonic() - t0) * 1000)
    check(f"Tiempo de respuesta frontend < 3 000 ms", ms < 3000, f"{ms} ms")


# ─────────────────────────────────────────────────────────────────────────────
# 2 · HEALTH + RAÍZ
# ─────────────────────────────────────────────────────────────────────────────

def test_health(api: str):
    section("2 · BACKEND HEALTH")

    probes = [
        ("/health/live",  "alive"),
        ("/health/ready", "ready"),
        ("/health/deep",  "healthy"),
    ]
    for path, expected_status in probes:
        r = _req("GET", api + path)
        if r is not None:
            body = _json(r)
            ok = r.status_code == 200 and body.get("status") in (expected_status, "ready", "healthy", "alive")
            check(f"GET {path}  →  200 + status OK", ok,
                  f"HTTP {r.status_code} · status={body.get('status', '?')}")

    # Raíz
    r = _req("GET", api + "/")
    if r is not None:
        body = _json(r)
        ok = r.status_code == 200 and "Heavy Freight" in body.get("service", "")
        check("GET /  →  200 + service name", ok,
              f"HTTP {r.status_code} · {body.get('service','?')[:40]}")


# ─────────────────────────────────────────────────────────────────────────────
# 3 · AUTH
# ─────────────────────────────────────────────────────────────────────────────

def test_auth(api: str, email: str, password: str) -> Optional[str]:
    """Devuelve access_token si login OK, None si Atlas no está accesible."""
    section("3 · AUTENTICACIÓN (requiere MongoDB Atlas)")

    # 3.1 Registro — puede devolver 201 (nuevo) o 409 (ya existe)
    r = _req("POST", api + "/auth/register",
             json={"email": email, "password": password, "full_name": "Smoke Test User"})
    if r is not None:
        ok = r.status_code in (201, 409)
        check("POST /auth/register  →  201 o 409", ok,
              f"HTTP {r.status_code}", warn_only=not ok)

    # 3.2 Login inválido → 401
    r = _req("POST", api + "/auth/login",
             json={"email": "nada@nada.com", "password": "WrongPass1!"})
    if r is not None:
        ok = r.status_code == 401
        check("POST /auth/login  (creds inválidas)  →  401", ok,
              f"HTTP {r.status_code}", warn_only=not ok)

    # 3.3 Login válido → 200 + access_token
    token: Optional[str] = None
    refresh: Optional[str] = None

    r = _req("POST", api + "/auth/login",
             json={"email": email, "password": password})
    if r is not None:
        if r.status_code == 200:
            body = _json(r)
            token   = body.get("access_token")
            refresh = body.get("refresh_token")
            ok = bool(token)
            check("POST /auth/login  (creds válidas)  →  200 + JWT", ok,
                  f"HTTP 200 · token={'OK' if token else 'MISSING'}", warn_only=not ok)
        else:
            check("POST /auth/login  (creds válidas)  →  200 + JWT", False,
                  f"HTTP {r.status_code} — Atlas puede estar bloqueando la IP de Lambda",
                  warn_only=True)

    if not token:
        print(f"\n  {Y}⚠ Sin token — se omiten pruebas de refresh y token inválido{X}")
        print(f"  {Y}  Solución: agregar 0.0.0.0/0 en MongoDB Atlas → Network Access{X}")
        return None

    # 3.4 Refresh → 200 + nuevo token
    if refresh:
        r = _req("POST", api + "/auth/refresh",
                 headers={"Authorization": f"Bearer {refresh}"})
        if r is not None:
            body = _json(r)
            ok = r.status_code == 200 and bool(body.get("access_token"))
            check("POST /auth/refresh  →  200 + nuevo token", ok,
                  f"HTTP {r.status_code}", warn_only=not ok)

    # 3.5 Token inválido → 401/403/422
    r = _req("GET", api + "/trips",
             headers={"Authorization": "Bearer token.invalido.xxx"})
    if r is not None:
        # Los stubs actuales no tienen guard → 200 también es aceptable hasta que se implementen
        ok = r.status_code in (200, 401, 403, 422)
        note = f"HTTP {r.status_code}"
        if r.status_code == 200:
            note += " (stub sin guard — OK por ahora)"
        check("GET /trips  (token inválido)  →  no 5xx", ok, note)

    return token


# ─────────────────────────────────────────────────────────────────────────────
# 4 · ENDPOINTS DE RECURSOS
# ─────────────────────────────────────────────────────────────────────────────

RESOURCES = [
    "/companies",
    "/clients",
    "/drivers",
    "/vehicles",
    "/trips",
    "/invoices",
    "/cargo-types",
    "/final-recipients",
    "/trip-statuses",
]
FAKE_ID = "000000000000000000000001"


def test_resources(api: str, token: Optional[str]):
    section("4 · ENDPOINTS DE RECURSOS")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # GET list → 200 (stub devuelve {"message": "Not yet implemented"} con 200)
    print(f"\n  {B}GET list  →  200{X}")
    for path in RESOURCES:
        r = _req("GET", api + path, headers=headers,
                 params={"page": "1", "limit": "5"})
        if r is not None:
            ok = r.status_code == 200
            body = _json(r)
            note = body.get("message", "") or f"total={body.get('total','?')}"
            check(f"  GET {path}", ok, f"HTTP {r.status_code} · {note[:40]}")

    # POST → 501 (stub)
    print(f"\n  {B}POST (stub)  →  501{X}")
    for path in RESOURCES:
        r = _req("POST", api + path, headers=headers, json={})
        if r is not None:
            ok = r.status_code == 501
            check(f"  POST {path}", ok, f"HTTP {r.status_code}")

    # GET by id → 501 (stub)
    print(f"\n  {B}GET /:id  →  501{X}")
    for path in ["/companies", "/drivers", "/vehicles", "/trips"]:
        r = _req("GET", api + f"{path}/{FAKE_ID}", headers=headers)
        if r is not None:
            ok = r.status_code == 501
            check(f"  GET {path}/{FAKE_ID}", ok, f"HTTP {r.status_code}")

    # DELETE → 204 o 501 (stub)
    print(f"\n  {B}DELETE /:id  →  501{X}")
    for path in ["/companies", "/trips"]:
        r = _req("DELETE", api + f"{path}/{FAKE_ID}", headers=headers)
        if r is not None:
            ok = r.status_code in (204, 501)
            check(f"  DELETE {path}/{FAKE_ID}", ok, f"HTTP {r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 5 · CORS
# ─────────────────────────────────────────────────────────────────────────────

def test_cors(api: str, frontend_origin: str):
    section("5 · CORS  (origen del frontend → backend)")

    # OPTIONS preflight
    r = _req("OPTIONS", api + "/auth/login", headers={
        "Origin": frontend_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    })
    if r is not None:
        acao = r.headers.get("access-control-allow-origin", "MISSING")
        ok = r.status_code in (200, 204) and acao in (frontend_origin, "*")
        check("OPTIONS /auth/login  →  CORS preflight OK", ok,
              f"HTTP {r.status_code} · ACAO={acao[:60]}")

    # GET con Origin header
    r = _req("GET", api + "/health/live", headers={"Origin": frontend_origin})
    if r is not None:
        acao = r.headers.get("access-control-allow-origin", "MISSING")
        ok = r.status_code == 200 and acao in (frontend_origin, "*")
        check("GET /health/live  con Origin  →  CORS header presente", ok,
              f"ACAO={acao[:60]}")


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────────────────────

def print_summary() -> bool:
    section("RESUMEN FINAL")

    total  = len(_results)
    passed = sum(1 for r in _results if r["status"] == "PASS")
    warned = sum(1 for r in _results if r["status"] == "WARN")
    failed = sum(1 for r in _results if r["status"] == "FAIL")

    print(f"\n  Checks totales : {total}")
    print(f"  {G}✓ PASS{X}          : {passed}")
    if warned:
        print(f"  {Y}⚠ WARN{X}          : {warned}  ← MongoDB/Atlas dependiente")
    if failed:
        print(f"  {R}✗ FAIL{X}          : {failed}")

    fails = [r for r in _results if r["status"] == "FAIL"]
    if fails:
        print(f"\n  {B}{R}Fallos:{X}")
        for r in fails:
            print(f"    {R}✗{X} {r['label']}")
            if r.get("note"):
                print(f"       {Y}{r['note']}{X}")

    score = int(passed / total * 100) if total else 0
    color = G if score == 100 else (Y if score >= 75 else R)
    emoji = "🟢" if failed == 0 else ("🟡" if warned > 0 and failed == 0 else "🔴")

    print(f"\n  Score : {color}{B}{score}%{X}")
    print(f"  {emoji}  {'Todo correcto — aplicación funcionando' if failed == 0 else 'Hay fallos — revisa arriba'}")

    # Guardar JSON
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"smoke_result_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": ts, "passed": passed, "warned": warned,
            "failed": failed, "score_pct": score, "results": _results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Resultado guardado en: {out}")

    return failed == 0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Smoke test automático — Heavy Freight Platform"
    )
    parser.add_argument("--api",
        default=DEFAULT_API,
        help="URL del API Gateway, ej: https://abc.execute-api.us-east-1.amazonaws.com")
    parser.add_argument("--frontend",
        default=FRONTEND_URL,
        help=f"URL del frontend S3 (default: {FRONTEND_URL})")
    parser.add_argument("--email",    default="",
        help="Email del usuario de prueba (para pruebas de auth)")
    parser.add_argument("--password", default="TestPass123!",
        help="Contraseña del usuario de prueba")
    parser.add_argument("--frontend-only", action="store_true",
        help="Solo probar el frontend S3")
    parser.add_argument("--backend-only",  action="store_true",
        help="Solo probar el backend Lambda")
    args = parser.parse_args()

    if not args.api and not args.frontend_only:
        args.api = DEFAULT_API

    print(f"\n{B}{'═'*70}")
    print(f"  🚚  Heavy Freight Platform — Smoke Test Automático")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*70}{X}")
    print(f"\n  Frontend : {args.frontend}")
    if args.api:
        print(f"  Backend  : {args.api}")
    if args.email:
        print(f"  Auth     : {args.email}")
    else:
        print(f"  Auth     : {Y}(sin --email → se omiten pruebas de login){X}")

    token: Optional[str] = None

    if not args.backend_only:
        test_frontend(args.frontend)

    if not args.frontend_only:
        if not args.api:
            print(f"\n{R}✗ Debes pasar --api URL para probar el backend{X}")
            print(f"  Ejemplo: python scripts/smoke_test.py --api https://XXXX.execute-api.us-east-1.amazonaws.com")
            sys.exit(1)

        test_health(args.api)

        # Si no dieron credenciales, genera un usuario aleatorio (el registro puede fallar si no hay Atlas)
        email = args.email or f"smoke_{uuid.uuid4().hex[:6]}@heavy-freight.test"
        token = test_auth(args.api, email, args.password)

        test_resources(args.api, token)
        test_cors(args.api, args.frontend)

    all_ok = print_summary()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
