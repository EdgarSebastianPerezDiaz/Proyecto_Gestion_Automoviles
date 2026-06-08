#!/usr/bin/env python3
"""
run_tests.py — Heavy Freight Platform — Auto Smoke Test
=======================================================
Script de ejecución automática. Descubre la URL del backend desde
serverless info, corre todos los checks y guarda el reporte.

Uso:
    python scripts/run_tests.py
    python scripts/run_tests.py --api https://XXXX.execute-api.us-east-1.amazonaws.com
    python scripts/run_tests.py --api URL --email admin@x.com --password Pass123!
"""

import os
import sys
import json
import time
import subprocess
import argparse
import re
import traceback
from datetime import datetime
from pathlib import Path

# ── ensure requests is available ─────────────────────────────────────────────
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Instalando requests...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

# ─────────────────────────────────────────────────────────────────────────────
# Configuración fija
# ─────────────────────────────────────────────────────────────────────────────

FRONTEND_URL = "http://heavy-freight-frontend-prod.s3-website-us-east-1.amazonaws.com"
TIMEOUT      = 15
BACKEND_DIR  = Path(__file__).parent.parent / "backend"

GREEN  = "\033[92m"; RED   = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD  = "\033[1m";  RESET  = "\033[0m"

results: list[dict] = []

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

S = make_session()


def check(label: str, fn, *args, **kwargs):
    start = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        ms  = int((time.monotonic() - start) * 1000)
        ok  = result.get("ok", True)
        tag = f"{GREEN}✅ PASS{RESET}" if ok else f"{RED}❌ FAIL{RESET}"
        note = result.get("note", "")
        print(f"  {tag}  {label:<55} {ms:>5}ms  {note}")
        results.append({"label": label, "ok": ok, "ms": ms,
                         "note": note, "detail": result.get("detail", "")})
        return result
    except Exception as exc:
        ms  = int((time.monotonic() - start) * 1000)
        msg = str(exc)[:100]
        print(f"  {RED}❌ ERR {RESET}  {label:<55} {ms:>5}ms  {msg}")
        results.append({"label": label, "ok": False, "ms": ms,
                         "note": msg, "detail": traceback.format_exc()})
        return {"ok": False}


def hdr(title: str):
    print(f"\n{BOLD}{CYAN}{'─'*72}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*72}{RESET}")


def get(url, headers=None, params=None, expected=200):
    r = S.get(url, headers=headers, params=params, timeout=TIMEOUT)
    return {"ok": r.status_code == expected, "note": f"HTTP {r.status_code}",
            "detail": r.text[:200], "response": r}


def post(url, payload, headers=None, expected=200):
    r = S.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    return {"ok": r.status_code == expected, "note": f"HTTP {r.status_code}",
            "detail": r.text[:200], "response": r}


def json_body(res: dict) -> dict:
    r = res.get("response")
    if r is None:
        return {}
    ct = r.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            return r.json()
        except Exception:
            pass
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# Auto-discover backend URL via `serverless info`
# ─────────────────────────────────────────────────────────────────────────────

def discover_api_url(stage: str = "prod") -> str | None:
    print(f"\n  🔍 Buscando URL del backend (serverless info --stage {stage})...")
    try:
        proc = subprocess.run(
            ["npx", "serverless", "info", "--stage", stage],
            cwd=str(BACKEND_DIR),
            capture_output=True, text=True, timeout=60
        )
        output = proc.stdout + proc.stderr
        # Buscar líneas como "  ANY - https://xxxx.execute-api..."
        matches = re.findall(
            r"https://[a-z0-9]+\.execute-api\.[a-z0-9-]+\.amazonaws\.com[^\s\"']*",
            output
        )
        if matches:
            # Limpiar el proxy path /{proxy+} si viene en la URL
            url = matches[0].split("/{")[0].rstrip("/")
            print(f"  ✅ URL encontrada: {url}")
            return url
        else:
            print(f"  {YELLOW}⚠ serverless info no devolvió URL. Stack no deployado aún.{RESET}")
            return None
    except Exception as e:
        print(f"  {YELLOW}⚠ No se pudo ejecutar serverless info: {e}{RESET}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 1 — Frontend S3
# ─────────────────────────────────────────────────────────────────────────────

def test_frontend(base: str):
    hdr("1 · FRONTEND S3 — Accesibilidad y SPA routing")

    # Carga raíz
    def _root():
        r = S.get(base + "/", timeout=TIMEOUT)
        ok = r.status_code == 200 and "<!doctype html" in r.text.lower()
        return {"ok": ok, "note": f"HTTP {r.status_code} · {'HTML ✓' if ok else '⚠ sin HTML'}"}
    check("GET / → index.html Angular", _root)

    # SPA fallback en rutas de la app
    for path in ["/login", "/admin", "/operator"]:
        def _spa(p=path):
            r = S.get(base + p, timeout=TIMEOUT)
            has_html = "<!doctype html" in r.text.lower()
            ok = has_html  # S3 error-document index.html debería servir Angular en todas las rutas
            return {"ok": ok, "note": f"HTTP {r.status_code} · {'SPA ✓' if ok else '⚠ no es Angular HTML'}"}
        check(f"SPA routing {path} → Angular app", _spa)

    # Tiempo de respuesta
    def _perf():
        t0 = time.monotonic()
        S.get(base + "/", timeout=TIMEOUT)
        ms = int((time.monotonic() - t0) * 1000)
        ok = ms < 3000
        return {"ok": ok, "note": f"{ms}ms {'< 3s ✓' if ok else '> 3s lento'}"}
    check("Tiempo de respuesta raíz < 3 000 ms", _perf)

    # Content-Type HTML correcto
    def _ct():
        r = S.get(base + "/", timeout=TIMEOUT)
        ct = r.headers.get("Content-Type", "")
        ok = "text/html" in ct
        return {"ok": ok, "note": f"Content-Type: {ct[:60]}"}
    check("Content-Type: text/html", _ct)

    # Verifica que cargue el JS bundle principal (Angular)
    def _bundle():
        r = S.get(base + "/", timeout=TIMEOUT)
        # El index.html de Angular tiene <script type="module" src="main-....js">
        has_script = "main" in r.text and (".js" in r.text)
        return {"ok": has_script, "note": "bundle JS referenciado en HTML" if has_script else "⚠ no se detectó bundle JS"}
    check("index.html referencia bundle Angular JS", _bundle)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2 — Backend público
# ─────────────────────────────────────────────────────────────────────────────

def test_backend_public(api: str):
    hdr("2 · BACKEND API — Endpoints públicos")

    def _live():
        res = get(f"{api}/health/live")
        body = json_body(res)
        ok = res["ok"] and body.get("status") == "alive"
        return {"ok": ok, "note": f"HTTP {res['response'].status_code} · status={body.get('status','?')}"}
    check("GET /health/live → {status: alive}", _live)

    def _ready():
        res = get(f"{api}/health/ready")
        body = json_body(res)
        ok = res["ok"] and body.get("status") in ("ready", "healthy")
        return {"ok": ok, "note": f"status={body.get('status','?')}"}
    check("GET /health/ready → {status: ready}", _ready)

    def _deep():
        res = get(f"{api}/health/deep")
        body = json_body(res)
        return {"ok": res["ok"], "note": f"HTTP {res['response'].status_code}"}
    check("GET /health/deep → 200", _deep)

    def _root():
        res = get(f"{api}/")
        body = json_body(res)
        ok = res["ok"] and "Heavy Freight" in body.get("service", "")
        return {"ok": ok, "note": body.get("service","?")[:50]}
    check("GET / → Heavy Freight Platform API", _root)

    def _login_bad():
        r = S.post(f"{api}/auth/login",
                   json={"email": "noexiste@invalid.com", "password": "WrongPass!"},
                   timeout=TIMEOUT)
        ok = r.status_code == 401
        return {"ok": ok, "note": f"HTTP {r.status_code} (esperado 401)"}
    check("POST /auth/login creds inválidas → 401", _login_bad)

    def _unauth():
        r = S.get(f"{api}/trips", timeout=TIMEOUT)
        ok = r.status_code in (401, 403, 422)
        return {"ok": ok, "note": f"HTTP {r.status_code} (esperado 401/403)"}
    check("GET /trips sin JWT → 401/403", _unauth)

    def _rate_limit():
        # 5 intentos de login falso — el 5to aún debe devolver 401, el 6to puede ser 429
        for i in range(5):
            S.post(f"{api}/auth/login",
                   json={"email": "ratetest@x.com", "password": "bad"},
                   timeout=TIMEOUT)
        r = S.post(f"{api}/auth/login",
                   json={"email": "ratetest@x.com", "password": "bad"},
                   timeout=TIMEOUT)
        ok = r.status_code in (401, 429)  # 429 = rate limited, 401 = aún permitido
        return {"ok": ok, "note": f"HTTP {r.status_code} tras 6 intentos"}
    check("Rate limit login: 6 intentos → 401 o 429", _rate_limit)

    def _cors_preflight():
        r = S.options(
            f"{api}/auth/login",
            headers={"Origin": FRONTEND_URL,
                     "Access-Control-Request-Method": "POST",
                     "Access-Control-Request-Headers": "Content-Type, Authorization"},
            timeout=TIMEOUT)
        acao = r.headers.get("access-control-allow-origin", "")
        ok = r.status_code in (200, 204) and (acao == FRONTEND_URL or acao == "*")
        return {"ok": ok, "note": f"HTTP {r.status_code} · ACAO={acao[:50] or 'MISSING'}"}
    check("OPTIONS /auth/login CORS preflight", _cors_preflight)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3 — Backend protegido (JWT)
# ─────────────────────────────────────────────────────────────────────────────

def test_backend_auth(api: str, email: str, password: str) -> str | None:
    hdr("3 · BACKEND API — Endpoints protegidos (JWT)")

    token = None
    refresh = None

    def _login():
        nonlocal token, refresh
        r = S.post(f"{api}/auth/login",
                   json={"email": email, "password": password}, timeout=TIMEOUT)
        if r.status_code == 200:
            body = r.json()
            token   = body.get("access_token")
            refresh = body.get("refresh_token")
            ok = bool(token and refresh)
            return {"ok": ok, "note": f"HTTP 200 · access={'✓' if token else '✗'} refresh={'✓' if refresh else '✗'}"}
        return {"ok": False, "note": f"HTTP {r.status_code} · {r.text[:80]}"}
    check(f"POST /auth/login ({email})", _login)

    if not token:
        print(f"\n  {YELLOW}⚠ Login fallido — omitiendo tests protegidos{RESET}")
        return None

    ah = {"Authorization": f"Bearer {token}"}

    # GET de todos los recursos del dominio
    endpoints = [
        ("/companies",        "Empresas"),
        ("/clients",          "Clientes"),
        ("/drivers",          "Conductores"),
        ("/vehicles",         "Vehículos"),
        ("/trips",            "Viajes"),
        ("/invoices",         "Facturas"),
        ("/cargo-types",      "Tipos de carga"),
        ("/final-recipients", "Destinatarios finales"),
        ("/trip-statuses",    "Estados de viaje"),
    ]

    for path, label in endpoints:
        def _ep(p=path, lbl=label):
            r = S.get(f"{api}{p}", headers=ah,
                      params={"page": "1", "limit": "5"}, timeout=TIMEOUT)
            ok = r.status_code in (200, 204)
            body = {}
            if "application/json" in r.headers.get("content-type",""):
                try:
                    body = r.json()
                except Exception:
                    pass
            total = body.get("total", body.get("count", "?")) if isinstance(body, dict) else "?"
            return {"ok": ok, "note": f"HTTP {r.status_code} · total={total}"}
        check(f"GET {path:<22} ({label})", _ep)

    # Refresh token
    def _refresh():
        if not refresh:
            return {"ok": False, "note": "sin refresh_token"}
        r = S.post(f"{api}/auth/refresh",
                   json={"refresh_token": refresh}, timeout=TIMEOUT)
        ok = r.status_code == 200
        if ok:
            body = r.json()
            ok = bool(body.get("access_token"))
        return {"ok": ok, "note": f"HTTP {r.status_code}"}
    check("POST /auth/refresh → nuevo access_token", _refresh)

    # Token inválido debe rechazarse
    def _bad_token():
        r = S.get(f"{api}/trips",
                  headers={"Authorization": "Bearer token.invalido.xxxxxx"},
                  timeout=TIMEOUT)
        ok = r.status_code in (401, 403, 422)
        return {"ok": ok, "note": f"HTTP {r.status_code} (esperado 401/403)"}
    check("GET /trips con token manipulado → 401/403", _bad_token)

    return token


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 4 — CORS end-to-end
# ─────────────────────────────────────────────────────────────────────────────

def test_cors(api: str, token: str | None):
    hdr("4 · CORS — Origen del frontend hacia el backend")

    def _cors_get():
        hdrs = {"Origin": FRONTEND_URL}
        if token:
            hdrs["Authorization"] = f"Bearer {token}"
        r = S.get(f"{api}/health/live", headers=hdrs, timeout=TIMEOUT)
        acao = r.headers.get("access-control-allow-origin", "")
        ok = r.status_code == 200 and (acao == FRONTEND_URL or acao == "*")
        return {"ok": ok, "note": f"ACAO={acao[:60] or 'MISSING'}"}
    check("GET /health/live con Origin: S3 → CORS OK", _cors_get)

    def _cors_trips():
        r = S.options(f"{api}/trips", headers={
            "Origin": FRONTEND_URL,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        }, timeout=TIMEOUT)
        acao = r.headers.get("access-control-allow-origin", "")
        acam = r.headers.get("access-control-allow-methods", "")
        ok = r.status_code in (200, 204) and (acao == FRONTEND_URL or acao == "*")
        return {"ok": ok, "note": f"HTTP {r.status_code} · methods: {acam[:40]}"}
    check("OPTIONS /trips preflight → CORS completo", _cors_trips)

    def _cors_creds():
        r = S.options(f"{api}/auth/login", headers={
            "Origin": FRONTEND_URL,
            "Access-Control-Request-Method": "POST",
        }, timeout=TIMEOUT)
        acac = r.headers.get("access-control-allow-credentials", "")
        return {"ok": acac.lower() == "true", "note": f"allow-credentials: {acac or 'MISSING'}"}
    check("CORS allow-credentials: true en /auth/login", _cors_creds)


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────────────────────

def summary() -> bool:
    hdr("RESUMEN FINAL")
    total  = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    score  = int(passed / total * 100) if total else 0

    print(f"\n  Total   : {total}")
    print(f"  {GREEN}Passed{RESET}  : {passed}")
    print(f"  {RED}Failed{RESET}  : {failed}")

    if failed:
        print(f"\n  {BOLD}{RED}Checks fallidos:{RESET}")
        for r in results:
            if not r["ok"]:
                print(f"    {RED}✗{RESET}  {r['label']}")
                if r.get("detail") and "Traceback" in r["detail"]:
                    line = [l for l in r["detail"].splitlines() if l.strip() and not l.startswith(" ")]
                    if line:
                        print(f"       {YELLOW}{line[-1][:100]}{RESET}")

    color  = GREEN if score == 100 else (YELLOW if score >= 75 else RED)
    verdict = "🟢 Todo OK" if failed == 0 else ("🟡 Parcial" if score >= 75 else "🔴 Fallos críticos")
    print(f"\n  Score  : {color}{BOLD}{score}%{RESET}  {verdict}")

    # Guardar JSON
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(__file__).parent / f"smoke_result_{ts}.json"
    out.write_text(json.dumps({
        "timestamp": ts, "frontend": FRONTEND_URL,
        "passed": passed, "failed": failed, "score_pct": score,
        "results": results
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  📄 Reporte JSON: {out}\n")
    return failed == 0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api",      default="",  help="URL del API Gateway")
    parser.add_argument("--stage",    default="prod")
    parser.add_argument("--email",    default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--frontend-only", action="store_true")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*72}")
    print(f"  🚚  Heavy Freight Platform — Smoke Test Automático")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S  (hora local)')}")
    print(f"{'═'*72}{RESET}")

    # Descubrir URL del backend si no se pasó
    api_url = args.api.rstrip("/")
    if not api_url and not args.frontend_only:
        api_url = (discover_api_url(args.stage) or "").rstrip("/")

    print(f"\n  Frontend : {FRONTEND_URL}")
    if api_url:
        print(f"  Backend  : {api_url}")
        print(f"  Auth     : {args.email or '(sin credenciales — solo endpoints públicos)'}")
    else:
        print(f"  Backend  : {YELLOW}no disponible (backend no deployado aún){RESET}")

    # ── Tests ────────────────────────────────────────────────────────────────
    test_frontend(FRONTEND_URL)

    token = None
    if api_url:
        test_backend_public(api_url)

        if args.email and args.password:
            token = test_backend_auth(api_url, args.email, args.password)
        else:
            hdr("3 · BACKEND API — Endpoints protegidos (JWT)")
            print(f"  {YELLOW}⚠ Pasa --email y --password para probar endpoints con JWT{RESET}")
            print(f"     Ejemplo: python scripts/run_tests.py --api {api_url} --email tu@email.com --password TuPass123!")

        test_cors(api_url, token)

    else:
        hdr("2–4 · BACKEND — Omitido (stack no deployado)")
        print(f"  {YELLOW}Para probar el backend:{RESET}")
        print(f"  1. Configura los secrets en GitHub y haz push a main")
        print(f"  2. O deploya manualmente: cd backend && npx serverless deploy --stage prod")
        print(f"  3. Luego ejecuta: python scripts/run_tests.py --api <URL>")

    all_ok = summary()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
