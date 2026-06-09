"""
Frontend contract tests — verifies every API response matches what Angular services expect.
Checks field names, response shapes, HTTP methods, and JWT payload.
Run: python scripts/frontend_contract_test.py
"""
import sys, json, base64
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

API = "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com"
EMAIL = "admin@heavy-freight.com"
PASSWORD = "Admin123!"

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(name, ok, detail=""):
    tag = PASS if ok else FAIL
    msg = f"  {tag} {name}" + (f": {detail}" if detail else "")
    print(msg)
    results.append((name, ok, detail))

def has_fields(obj, fields, label=""):
    missing = [f for f in fields if f not in obj or obj[f] is None]
    ok = len(missing) == 0
    check(label or f"fields {fields}", ok, f"missing={missing}" if missing else "")
    return ok

def decode_jwt(token):
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        return {}

print("=" * 60)
print("HEAVY FREIGHT — Frontend Contract Tests")
print(f"API: {API}")
print("=" * 60)

# ── 1. AUTH ──────────────────────────────────────────────────
print("\n[AUTH]")
r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
check("POST /auth/login status 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code != 200:
    print("  Cannot continue without auth — aborting"); sys.exit(1)

body = r.json()
check("login has access_token", "access_token" in body)
check("login has refresh_token", "refresh_token" in body, "AuthService.storeTokens() needs it")

tok = body.get("access_token", "")
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

jwt_payload = decode_jwt(tok)
check("JWT has user_id",   "user_id"   in jwt_payload, f"got keys: {list(jwt_payload.keys())}")
check("JWT has full_name", "full_name" in jwt_payload, "AuthService.decodeToken() needs it")
check("JWT has email",     "email"     in jwt_payload)
check("JWT has role",      "role"      in jwt_payload)

# ── 2. COMPANIES ─────────────────────────────────────────────
print("\n[COMPANIES] — CompanyService expects: id, nombre, nit, direccion, telefono, correo")
r = requests.get(f"{API}/companies", headers=H, timeout=15)
check("GET /companies status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "company fields")

# ── 3. CLIENTS (transportista.service.ts calls /clients) ─────
print("\n[CLIENTS] — TransportistaService.getAll() (fixed: extracts .items from paginated)")
r = requests.get(f"{API}/clients", headers=H, timeout=15)
check("GET /clients status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
is_paginated = isinstance(data, dict) and "items" in data
check("response is paginated with items[] (TransportistaService now extracts .items)", is_paginated)
if is_paginated and data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "client fields")

# ── 4. DRIVERS ────────────────────────────────────────────────
print("\n[DRIVERS] — DriverService expects paginated with Spanish fields")
r = requests.get(f"{API}/drivers", headers=H, timeout=15)
check("GET /drivers status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "fullName", "cedula", "telefono", "correo", "direccion",
                      "numeroLicencia", "categoriaLicencia", "fechaVencimientoLicencia"], "driver fields")

# ── 5. VEHICLES ───────────────────────────────────────────────
print("\n[VEHICLES] — VehicleService expects paginated with placa/marca/modelo/capacidad/estado")
r = requests.get(f"{API}/vehicles", headers=H, timeout=15)
check("GET /vehicles status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "placa", "marca", "modelo", "capacidad", "transportistaId", "estado"], "vehicle fields")
    valid_estados = {"Disponible", "En Viaje", "Inactivo"}
    check("vehicle estado is Spanish", item.get("estado") in valid_estados,
          f"got '{item.get('estado')}' — must be one of {valid_estados}")

# ── 6. CARGO TYPES ────────────────────────────────────────────
print("\n[CARGO TYPES] — CargoTypeService expects: id, nombre, descripcion, precioPorTon")
r = requests.get(f"{API}/cargo-types", headers=H, timeout=15)
check("GET /cargo-types status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "descripcion", "precioPorTon"], "cargo_type fields")

# ── 7. FINAL RECIPIENTS ───────────────────────────────────────
print("\n[FINAL RECIPIENTS] — FinalRecipientService.getAll() (fixed: extracts .items from paginated)")
r = requests.get(f"{API}/final-recipients", headers=H, timeout=15)
check("GET /final-recipients status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
is_paginated = isinstance(data, dict) and "items" in data
check("response is paginated with items[] (FinalRecipientService now extracts .items)", is_paginated)
if is_paginated and data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "recipient fields")

# ── 8. TRIP STATUSES ──────────────────────────────────────────
print("\n[TRIP STATUSES] — expects paginated with nombre, descripcion")
r = requests.get(f"{API}/trip-statuses", headers=H, timeout=15)
check("GET /trip-statuses status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "descripcion"], "trip_status fields")

# ── 9. TRIPS ──────────────────────────────────────────────────
print("\n[TRIPS] — TripService expects paginated with fechaSalida/peso/costoTotal/estado")
r = requests.get(f"{API}/trips", headers=H, timeout=15)
check("GET /trips status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "fechaSalida", "fechaLlegadaEstimada", "peso",
                      "costoTotal", "vehiculoId", "conductorId", "estado"], "trip fields")
    trip_id = item.get("id", "")

    # Test PATCH /trips/{id}/status (frontend uses PATCH, router has PUT)
    print("\n[TRIPS - status update]")
    r_patch = requests.patch(f"{API}/trips/{trip_id}/status",
                             headers=H, json={"estado": "En Ruta"}, timeout=15)
    check("PATCH /trips/{id}/status accepted (not 405)", r_patch.status_code != 405,
          f"got {r_patch.status_code} — frontend TripService.updateTripStatus uses http.patch()")
    check("PATCH /trips/{id}/status status 200", r_patch.status_code == 200,
          f"got {r_patch.status_code} body={r_patch.text[:120]}")

# ── 10. INVOICES ──────────────────────────────────────────────
print("\n[INVOICES] — expects paginated with numeroFactura/monto/impuesto/total/estado")
r = requests.get(f"{API}/invoices", headers=H, timeout=15)
check("GET /invoices status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "numeroFactura", "monto", "impuesto", "total", "estado"], "invoice fields")

# ── SUMMARY ───────────────────────────────────────────────────
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print("\n" + "=" * 60)
print(f"RESULTS: {passed}/{total} passed  |  {failed} failed")
print("=" * 60)
if failed:
    print("\nFailed tests:")
    for name, ok, detail in results:
        if not ok:
            print(f"  {FAIL} {name}: {detail}")
sys.exit(0 if failed == 0 else 1)
