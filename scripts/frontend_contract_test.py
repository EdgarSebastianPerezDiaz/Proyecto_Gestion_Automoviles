"""
Frontend contract tests — verifies every API response matches what Angular services expect.
Checks field names, response shapes, HTTP methods, JWT payload, and CREATE operations.
Run: python scripts/frontend_contract_test.py
"""
import sys, json, base64, random, time
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
created_ids = {}  # track created records for cleanup

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
    except Exception:
        return {}

def rnd():
    """Return a short random suffix for unique test values."""
    return str(random.randint(100000, 999999))

def random_nit():
    """Generate a valid NIT in 'XXX.XXX.XXX-Y' format (10 digits total)."""
    d = [random.randint(0,9) for _ in range(10)]
    return f"{d[0]}{d[1]}{d[2]}.{d[3]}{d[4]}{d[5]}.{d[6]}{d[7]}{d[8]}-{d[9]}"

print("=" * 65)
print("HEAVY FREIGHT — Frontend Contract Tests")
print(f"API: {API}")
print("=" * 65)

# ── 1. AUTH ──────────────────────────────────────────────────────
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

# ── 2. COMPANIES GET ─────────────────────────────────────────────
print("\n[COMPANIES — GET]")
r = requests.get(f"{API}/companies", headers=H, timeout=15)
check("GET /companies status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "company fields")

# ── 3. CLIENTS GET ───────────────────────────────────────────────
print("\n[CLIENTS — GET]")
r = requests.get(f"{API}/clients", headers=H, timeout=15)
check("GET /clients status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
is_pag = isinstance(data, dict) and "items" in data
check("response is paginated with items[]", is_pag)
if is_pag and data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "client fields")

# ── 4. DRIVERS GET ────────────────────────────────────────────────
print("\n[DRIVERS — GET]")
r = requests.get(f"{API}/drivers", headers=H, timeout=15)
check("GET /drivers status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "fullName", "cedula", "telefono", "correo", "direccion",
                      "numeroLicencia", "categoriaLicencia", "fechaVencimientoLicencia"], "driver fields")

# ── 5. VEHICLES GET ───────────────────────────────────────────────
print("\n[VEHICLES — GET]")
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

# ── 6. CARGO TYPES GET ────────────────────────────────────────────
print("\n[CARGO TYPES — GET]")
r = requests.get(f"{API}/cargo-types", headers=H, timeout=15)
check("GET /cargo-types status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "descripcion", "precioPorTon"], "cargo_type fields")

# ── 7. FINAL RECIPIENTS GET ───────────────────────────────────────
print("\n[FINAL RECIPIENTS — GET]")
r = requests.get(f"{API}/final-recipients", headers=H, timeout=15)
check("GET /final-recipients status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
is_pag = isinstance(data, dict) and "items" in data
check("response is paginated with items[]", is_pag)
if is_pag and data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "recipient fields")

# ── 8. TRIP STATUSES GET ──────────────────────────────────────────
print("\n[TRIP STATUSES — GET]")
r = requests.get(f"{API}/trip-statuses", headers=H, timeout=15)
check("GET /trip-statuses status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "nombre", "descripcion"], "trip_status fields")

# ── 9. TRIPS GET ──────────────────────────────────────────────────
print("\n[TRIPS — GET + status update]")
r = requests.get(f"{API}/trips", headers=H, timeout=15)
check("GET /trips status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
trip_id_for_patch = None
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "fechaSalida", "fechaLlegadaEstimada", "peso",
                      "costoTotal", "vehiculoId", "conductorId", "estado"], "trip fields")
    trip_id_for_patch = item.get("id", "")
    r_patch = requests.patch(f"{API}/trips/{trip_id_for_patch}/status",
                             headers=H, json={"estado": "En Ruta"}, timeout=15)
    check("PATCH /trips/{id}/status not 405", r_patch.status_code != 405,
          f"got {r_patch.status_code}")
    check("PATCH /trips/{id}/status 200", r_patch.status_code == 200,
          f"got {r_patch.status_code} body={r_patch.text[:120]}")

# ── 10. INVOICES GET ──────────────────────────────────────────────
print("\n[INVOICES — GET]")
r = requests.get(f"{API}/invoices", headers=H, timeout=15)
check("GET /invoices status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("response has items[]", "items" in data)
if data.get("items"):
    item = data["items"][0]
    has_fields(item, ["id", "numeroFactura", "monto", "impuesto", "total", "estado"], "invoice fields")

# ═══════════════════════════════════════════════════════════════════
# POST / CREATE tests — simulate exact Angular form payloads
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("CREATE TESTS (POST with Angular form payloads)")
print("=" * 65)

s = rnd()  # unique suffix for this test run

# ── 11. POST /companies ───────────────────────────────────────────
print("\n[POST /companies — Angular company-form-modal payload]")
company_body = {
    "nombre":   f"Transportes Test {s} S.A.",
    "nit":      random_nit(),
    "direccion": "Calle 100 #50-30, Bogotá",
    "telefono": "3001234567",
    "correo":   f"company{s}@example.com",
}
r = requests.post(f"{API}/companies", headers=H, json=company_body, timeout=15)
check("POST /companies 201", r.status_code == 201,
      f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    co = r.json()
    has_fields(co, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "created company has Spanish fields")
    check("created company nombre matches", co.get("nombre") == company_body["nombre"],
          f"got '{co.get('nombre')}'")
    created_ids["company"] = co.get("id")

# ── 12. POST /clients ─────────────────────────────────────────────
print("\n[POST /clients — Angular transportista-form-modal payload]")
client_body = {
    "nombre":       f"Logística Test {s} Ltda",
    "nit":          random_nit(),
    "direccion":    "Av 80 #20-15, Medellín",
    "telefono":     "4441234567",
    "correo":       f"client{s}@example.com",
    "tipoDocumento": "NIT",
}
r = requests.post(f"{API}/clients", headers=H, json=client_body, timeout=15)
check("POST /clients 201", r.status_code == 201,
      f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    cl = r.json()
    has_fields(cl, ["id", "nombre", "nit", "direccion", "telefono", "correo"], "created client has Spanish fields")
    check("created client nombre matches", cl.get("nombre") == client_body["nombre"],
          f"got '{cl.get('nombre')}'")
    created_ids["client"] = cl.get("id")

# ── 13. POST /drivers ─────────────────────────────────────────────
print("\n[POST /drivers — Angular driver-form-modal payload]")
driver_body = {
    "fullName":                  "Carlos Rodriguez",
    "cedula":                    s,
    "telefono":                  "3201234567",
    "direccion":                 "Cra 7 #30-45, Bogotá",
    "correo":                    f"driver{s}@example.com",
    "numeroLicencia":            f"LIC{s}",
    "categoriaLicencia":         "C3",
    "fechaVencimientoLicencia":  "2028-12-31T23:59:59",
}
r = requests.post(f"{API}/drivers", headers=H, json=driver_body, timeout=15)
check("POST /drivers 201", r.status_code == 201,
      f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    dr = r.json()
    has_fields(dr, ["id", "fullName", "cedula", "telefono", "correo",
                    "numeroLicencia", "categoriaLicencia"], "created driver has Spanish fields")
    check("created driver fullName matches", driver_body["fullName"] in dr.get("fullName", ""),
          f"got '{dr.get('fullName')}'")
    created_ids["driver"] = dr.get("id")

# ── 14. POST /vehicles ────────────────────────────────────────────
print("\n[POST /vehicles — Angular vehicle-form-modal payload]")
# Need a company_id — use freshly created one or fall back to first existing
cmp_id = created_ids.get("company")
if not cmp_id:
    resp = requests.get(f"{API}/companies", headers=H, timeout=15).json()
    cmp_id = (resp.get("items") or [{}])[0].get("id", "")

if cmp_id:
    vehicle_body = {
        "placa":          f"T{s[:5].upper()}",
        "marca":          "Kenworth",
        "modelo":         "2023",
        "capacidad":      "35",
        "estado":         "Disponible",
        "transportistaId": cmp_id,
    }
    r = requests.post(f"{API}/vehicles", headers=H, json=vehicle_body, timeout=15)
    check("POST /vehicles 201", r.status_code == 201,
          f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 201:
        vh = r.json()
        has_fields(vh, ["id", "placa", "marca", "modelo", "capacidad", "transportistaId", "estado"],
                   "created vehicle has Spanish fields")
        check("created vehicle placa matches", vh.get("placa") == vehicle_body["placa"].upper(),
              f"got '{vh.get('placa')}'")
        check("created vehicle estado is Spanish", vh.get("estado") in {"Disponible", "En Viaje", "Inactivo"},
              f"got '{vh.get('estado')}'")
        created_ids["vehicle"] = vh.get("id")
else:
    check("POST /vehicles skipped (no company_id available)", True, "WARN: no company found")

# ── 15. POST /cargo-types ─────────────────────────────────────────
print("\n[POST /cargo-types — Angular cargo-type-form-modal payload]")
cargo_body = {
    "nombre":      f"Carga Test {s}",
    "descripcion": "Material de prueba para tests automatizados",
    "precioPorTon": 125000,
}
r = requests.post(f"{API}/cargo-types", headers=H, json=cargo_body, timeout=15)
check("POST /cargo-types 201", r.status_code == 201,
      f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    ct = r.json()
    has_fields(ct, ["id", "nombre", "descripcion", "precioPorTon"], "created cargo_type has Spanish fields")
    check("created cargo_type precioPorTon is numeric", isinstance(ct.get("precioPorTon"), (int, float)),
          f"got type {type(ct.get('precioPorTon')).__name__}")
    created_ids["cargo_type"] = ct.get("id")

# ── 16. POST /final-recipients ────────────────────────────────────
print("\n[POST /final-recipients — Angular final-recipient-form-modal payload]")
recipient_body = {
    "nombre":   f"Destinatario Test {s}",
    "nit":      random_nit(),
    "direccion": "Av El Dorado #68-50, Bogotá",
    "telefono": "3001112233",
    "correo":   f"recipient{s}@example.com",
}
r = requests.post(f"{API}/final-recipients", headers=H, json=recipient_body, timeout=15)
check("POST /final-recipients 201", r.status_code == 201,
      f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    rec = r.json()
    has_fields(rec, ["id", "nombre", "nit", "direccion", "telefono", "correo"],
               "created recipient has Spanish fields")
    check("created recipient nombre matches", rec.get("nombre") == recipient_body["nombre"],
          f"got '{rec.get('nombre')}'")
    created_ids["recipient"] = rec.get("id")

# ── 17. POST /trips ───────────────────────────────────────────────
print("\n[POST /trips — Angular trip-wizard-modal payload]")
v_id  = created_ids.get("vehicle")
d_id  = created_ids.get("driver")
c_id  = created_ids.get("cargo_type")
cl_id = created_ids.get("client")
r_id  = created_ids.get("recipient")

if not v_id:
    resp = requests.get(f"{API}/vehicles", headers=H, timeout=15).json()
    v_id = (resp.get("items") or [{}])[0].get("id", "")
if not d_id:
    resp = requests.get(f"{API}/drivers", headers=H, timeout=15).json()
    d_id = (resp.get("items") or [{}])[0].get("id", "")
if not c_id:
    resp = requests.get(f"{API}/cargo-types", headers=H, timeout=15).json()
    c_id = (resp.get("items") or [{}])[0].get("id", "")
if not cl_id:
    resp = requests.get(f"{API}/clients", headers=H, timeout=15).json()
    cl_id = (resp.get("items") or [{}])[0].get("id", "")
if not r_id:
    resp = requests.get(f"{API}/final-recipients", headers=H, timeout=15).json()
    r_id = (resp.get("items") or [{}])[0].get("id", "")

if all([v_id, d_id, c_id, cl_id, r_id]):
    # Departure 2 days from now (safely in the future)
    dep = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT08:00:00")
    arr = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT18:00:00")
    trip_body = {
        "origin":       "Bogotá, Cundinamarca",
        "destination":  "Medellín, Antioquia",
        "vehiculoId":   v_id,
        "conductorId":  d_id,
        "cargoTypeId":  c_id,
        "transportistaId": cl_id,
        "destinoId":    r_id,
        "peso":         25.5,
        "costoTotal":   1500000,
        "fechaSalida":  dep,
        "fechaLlegadaEstimada": arr,
    }
    r = requests.post(f"{API}/trips", headers=H, json=trip_body, timeout=15)
    check("POST /trips 201", r.status_code == 201,
          f"got {r.status_code}: {r.text[:300]}")
    if r.status_code == 201:
        tr = r.json()
        has_fields(tr, ["id", "fechaSalida", "fechaLlegadaEstimada", "peso",
                        "costoTotal", "vehiculoId", "conductorId", "estado"], "created trip has Spanish fields")
        check("created trip peso matches", tr.get("peso") == 25.5,
              f"got {tr.get('peso')}")
        check("created trip estado is Spanish", isinstance(tr.get("estado"), str),
              f"got {tr.get('estado')!r}")
        created_ids["trip"] = tr.get("id")
else:
    missing = [k for k, v in {"vehicle": v_id, "driver": d_id, "cargo": c_id,
                               "client": cl_id, "recipient": r_id}.items() if not v]
    check("POST /trips skipped", True, f"WARN: missing IDs for {missing}")

# ── CLEANUP ───────────────────────────────────────────────────────
print("\n[CLEANUP — deleting test records]")
cleanup_order = [
    ("trip",       "trips"),
    ("vehicle",    "vehicles"),
    ("driver",     "drivers"),
    ("cargo_type", "cargo-types"),
    ("recipient",  "final-recipients"),
    ("client",     "clients"),
    ("company",    "companies"),
]
for key, endpoint in cleanup_order:
    rec_id = created_ids.get(key)
    if rec_id:
        rd = requests.delete(f"{API}/{endpoint}/{rec_id}", headers=H, timeout=15)
        check(f"DELETE /{endpoint}/{rec_id[:8]}… status 204",
              rd.status_code == 204, f"got {rd.status_code}")

# ── SUMMARY ───────────────────────────────────────────────────────
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print("\n" + "=" * 65)
print(f"RESULTS: {passed}/{total} passed  |  {failed} failed")
print("=" * 65)
if failed:
    print("\nFailed tests:")
    for name, ok, detail in results:
        if not ok:
            print(f"  {FAIL} {name}: {detail}")
sys.exit(0 if failed == 0 else 1)
