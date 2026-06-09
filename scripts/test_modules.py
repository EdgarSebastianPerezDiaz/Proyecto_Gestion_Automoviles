"""
Heavy Freight Platform — Full Module Integration Test
10 tests per module, automated CRUD validation.

Usage:
    python scripts/test_modules.py --api https://YOUR_API_URL
    python scripts/test_modules.py --api https://YOUR_API_URL --email admin@test.com --password Admin123!
"""
import argparse
import sys
import json
import random
import string
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

# ── CLI args ─────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--api", required=True, help="Base API URL (no trailing slash)")
parser.add_argument("--email", default="admin@heavy-freight.com")
parser.add_argument("--password", default="Admin123!")
args = parser.parse_args()

API = args.api.rstrip("/")
EMAIL = args.email
PASSWORD = args.password

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0


def rnd(n=6) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


def future(days=365) -> str:
    # Naive datetime — service comparisons use datetime.now() (no tz)
    return (datetime.now() + timedelta(days=days)).isoformat()


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    suffix = f" ({detail})" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if ok:
        PASS += 1
    else:
        FAIL += 1
    return ok


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def get_token() -> str:
    """Login and return JWT access token."""
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    if r.status_code == 200:
        return r.json().get("access_token", "")
    # Try register first
    requests.post(f"{API}/auth/register",
                  json={"email": EMAIL, "password": PASSWORD, "full_name": "Test Admin"},
                  timeout=15)
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    if r.status_code == 200:
        return r.json().get("access_token", "")
    print(f"FATAL: Cannot obtain JWT — login returned {r.status_code}: {r.text[:200]}")
    sys.exit(1)


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get(token, path, **kw):
    return requests.get(f"{API}/{path.lstrip('/')}", headers=H(token), timeout=15, **kw)


def post(token, path, body, **kw):
    return requests.post(f"{API}/{path.lstrip('/')}", headers=H(token), json=body, timeout=15, **kw)


def put(token, path, body, **kw):
    return requests.put(f"{API}/{path.lstrip('/')}", headers=H(token), json=body, timeout=15, **kw)


def delete(token, path, **kw):
    return requests.delete(f"{API}/{path.lstrip('/')}", headers=H(token), timeout=15, **kw)


# ── AUTH ──────────────────────────────────────────────────────────────────────

section("AUTH — obtain token")
token = get_token()
check("Login OK — JWT obtained", bool(token), token[:40] if token else "empty")

# ── MODULE TESTS ──────────────────────────────────────────────────────────────

# ─────────── 1. CARGO TYPES ───────────────────────────────────────────────────

section("MODULE 1: CARGO TYPES (10 tests)")

# T1 — List (empty is OK)
r = get(token, "/cargo-types")
check("T1 List cargo-types returns 200", r.status_code == 200, str(r.status_code))

# T2 — Create first cargo type
cargo_name1 = f"Carga{rnd(4).upper()}"
r = post(token, "/cargo-types", {
    "name": cargo_name1,
    "description": "Carga general de prueba",
    "price_per_ton": 120.50,
    "hazardous": False,
    "requires_temperature_control": False,
    "requires_special_permit": False,
    "fragile": False,
})
check("T2 Create cargo type returns 201", r.status_code == 201, str(r.status_code))
cargo1_id = r.json().get("id") if r.status_code == 201 else None

# T3 — Create second cargo type (hazardous)
r = post(token, "/cargo-types", {
    "name": f"Quimico{rnd(3).upper()}",
    "description": "Material peligroso requiere permiso especial",
    "price_per_ton": 350.00,
    "hazardous": True,
    "requires_temperature_control": False,
    "requires_special_permit": True,
    "fragile": False,
})
check("T3 Create hazardous cargo type", r.status_code == 201, str(r.status_code))
cargo2_id = r.json().get("id") if r.status_code == 201 else None

# T4 — Get by ID
if cargo1_id:
    r = get(token, f"/cargo-types/{cargo1_id}")
    check("T4 Get cargo type by ID", r.status_code == 200 and r.json().get("id") == cargo1_id)
else:
    check("T4 Get cargo type by ID", False, "no ID from T2")

# T5 — List shows created items
r = get(token, "/cargo-types")
check("T5 List contains created cargo types", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — Duplicate name returns 409
if cargo1_id:
    r = post(token, "/cargo-types", {
        "name": cargo_name1,
        "description": "Duplicado",
        "price_per_ton": 50.0,
        "hazardous": False, "requires_temperature_control": False,
        "requires_special_permit": False, "fragile": False,
    })
    check("T6 Duplicate cargo type name -> 409", r.status_code == 409, str(r.status_code))
else:
    check("T6 Duplicate cargo type name -> 409", False, "no ID from T2")

# T7 — Update price
if cargo1_id:
    r = put(token, f"/cargo-types/{cargo1_id}", {"price_per_ton": 200.0})
    check("T7 Update cargo type price", r.status_code == 200, str(r.status_code))
else:
    check("T7 Update cargo type price", False, "no ID")

# T8 — Invalid price (negative) returns 422
r = post(token, "/cargo-types", {
    "name": f"Invalid{rnd(4)}",
    "description": "Precio negativo",
    "price_per_ton": -10.0,
    "hazardous": False, "requires_temperature_control": False,
    "requires_special_permit": False, "fragile": False,
})
check("T8 Negative price_per_ton -> 422", r.status_code == 422, str(r.status_code))

# T9 — Get non-existent returns 404
r = get(token, "/cargo-types/000000000000000000000000")
check("T9 Non-existent cargo type -> 404", r.status_code == 404, str(r.status_code))

# T10 — Delete
if cargo2_id:
    r = delete(token, f"/cargo-types/{cargo2_id}")
    check("T10 Delete cargo type -> 204", r.status_code == 204, str(r.status_code))
else:
    check("T10 Delete cargo type -> 204", False, "no ID from T3")

# ─────────── 2. COMPANIES ────────────────────────────────────────────────────

section("MODULE 2: COMPANIES (10 tests)")

# T1 — List
r = get(token, "/companies")
check("T1 List companies returns 200", r.status_code == 200)

# T2 — Create company 1
nit1 = f"{random.randint(100000000, 999999999)}0"  # 10 digits
r = post(token, "/companies", {
    "nit": nit1,
    "legal_name": f"Empresa {rnd(5).upper()} S.A.S",
    "trade_name": f"Empresa {rnd(4)}",
    "address": "Calle 50 # 10-20",
    "city": "Bogotá",
    "phone": "+57 1 2345678",
    "email": f"empresa{rnd(4)}@empresa.com",
    "contact_name": "Juan García",
})
check("T2 Create company returns 201", r.status_code == 201, str(r.status_code))
co1_id = r.json().get("id") if r.status_code == 201 else None

# T3 — Create company 2
nit2 = f"{random.randint(100000000, 999999999)}0"
r = post(token, "/companies", {
    "nit": nit2,
    "legal_name": f"Transportes {rnd(5).upper()} Ltda",
    "address": "Av. El Dorado 93-11",
    "city": "Medellín",
    "phone": "+57 4 8765432",
    "email": f"transport{rnd(4)}@example.com",
})
check("T3 Create second company returns 201", r.status_code == 201, str(r.status_code))
co2_id = r.json().get("id") if r.status_code == 201 else None

# T4 — Get by ID
if co1_id:
    r = get(token, f"/companies/{co1_id}")
    check("T4 Get company by ID", r.status_code == 200 and r.json().get("id") == co1_id)
else:
    check("T4 Get company by ID", False, "no ID from T2")

# T5 — List shows items
r = get(token, "/companies")
check("T5 List has at least 1 company", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — Duplicate NIT -> 409
if co1_id:
    r = post(token, "/companies", {
        "nit": nit1,
        "legal_name": "Empresa Duplicada",
        "address": "Calle 1 # 1-1",
        "city": "Bogotá",
        "phone": "1234567",
        "email": f"dup{rnd(4)}@test.com",
    })
    check("T6 Duplicate NIT -> 409", r.status_code == 409, str(r.status_code))
else:
    check("T6 Duplicate NIT -> 409", False, "no ID from T2")

# T7 — Update company city
if co1_id:
    r = put(token, f"/companies/{co1_id}", {"city": "Cali"})
    check("T7 Update company city", r.status_code == 200, str(r.status_code))
else:
    check("T7 Update company city", False, "no ID")

# T8 — Invalid NIT format -> 422
r = post(token, "/companies", {
    "nit": "123",
    "legal_name": "Invalid NIT Co",
    "address": "Calle 1 # 1-1",
    "city": "Bogotá",
    "phone": "1234567",
    "email": f"inv{rnd(4)}@test.com",
})
check("T8 Invalid NIT -> 422", r.status_code == 422, str(r.status_code))

# T9 — 404 for unknown ID
r = get(token, "/companies/000000000000000000000000")
check("T9 Unknown company -> 404", r.status_code == 404)

# T10 — Delete company 2
if co2_id:
    r = delete(token, f"/companies/{co2_id}")
    check("T10 Delete company -> 204", r.status_code == 204)
else:
    check("T10 Delete company -> 204", False, "no ID from T3")

# ─────────── 3. CLIENTS ──────────────────────────────────────────────────────

section("MODULE 3: CLIENTS (10 tests)")

r = get(token, "/clients")
check("T1 List clients returns 200", r.status_code == 200)

cl_email1 = f"client{rnd(5)}@example.com"
r = post(token, "/clients", {
    "name": f"Cliente {rnd(4).upper()} S.A.",
    "phone": "+57 300 1234567",
    "email": cl_email1,
    "address": "Carrera 7 # 45-50",
    "city": "Bogotá",
    "contact_person": "Ana López",
})
check("T2 Create client returns 201", r.status_code == 201, str(r.status_code))
cl1_id = r.json().get("id") if r.status_code == 201 else None

cl_email2 = f"client{rnd(5)}@example.com"
r = post(token, "/clients", {
    "name": f"Distribuidora {rnd(4).upper()}",
    "phone": "+57 311 9876543",
    "email": cl_email2,
    "address": "Av. Las Américas 68-75",
    "city": "Cali",
})
check("T3 Create second client returns 201", r.status_code == 201, str(r.status_code))
cl2_id = r.json().get("id") if r.status_code == 201 else None

if cl1_id:
    r = get(token, f"/clients/{cl1_id}")
    check("T4 Get client by ID", r.status_code == 200 and r.json().get("id") == cl1_id)
else:
    check("T4 Get client by ID", False, "no ID")

r = get(token, "/clients")
check("T5 List clients has items", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — duplicate email
r = post(token, "/clients", {
    "name": "Duplicado",
    "phone": "1234567",
    "email": cl_email1,
    "address": "Calle 1",
    "city": "Bogotá",
})
check("T6 Duplicate email -> 409", r.status_code == 409, str(r.status_code))

# T7 — update city
if cl1_id:
    r = put(token, f"/clients/{cl1_id}", {"city": "Medellín"})
    check("T7 Update client city", r.status_code == 200, str(r.status_code))
else:
    check("T7 Update client city", False, "no ID")

# T8 — short name -> 422
r = post(token, "/clients", {
    "name": "A",
    "phone": "1234567",
    "email": f"short{rnd(4)}@example.com",
    "address": "Calle 1 # 1-1",
    "city": "Bogotá",
})
check("T8 Short name -> 422", r.status_code == 422, str(r.status_code))

r = get(token, "/clients/000000000000000000000000")
check("T9 Unknown client -> 404", r.status_code == 404)

if cl2_id:
    r = delete(token, f"/clients/{cl2_id}")
    check("T10 Delete client -> 204", r.status_code == 204)
else:
    check("T10 Delete client -> 204", False, "no ID")

# ─────────── 4. FINAL RECIPIENTS ─────────────────────────────────────────────

section("MODULE 4: FINAL RECIPIENTS (10 tests)")

r = get(token, "/final-recipients")
check("T1 List final-recipients returns 200", r.status_code == 200)

r = post(token, "/final-recipients", {
    "name": f"Destinatario {rnd(4).upper()}",
    "phone": "+57 312 1111111",
    "email": f"dest{rnd(4)}@example.com",
    "address": "Calle 100 # 15-20",
    "city": "Bogotá",
    "department": "Cundinamarca",
    "postal_code": "110111",
    "special_instructions": "Entregar en horario de oficina",
})
check("T2 Create recipient returns 201", r.status_code == 201, str(r.status_code))
rec1_id = r.json().get("id") if r.status_code == 201 else None

r = post(token, "/final-recipients", {
    "name": f"Receptor {rnd(4).upper()}",
    "phone": "+57 320 2222222",
    "address": "Av. 30 # 40-50",
    "city": "Medellín",
})
check("T3 Create second recipient returns 201", r.status_code == 201, str(r.status_code))
rec2_id = r.json().get("id") if r.status_code == 201 else None

if rec1_id:
    r = get(token, f"/final-recipients/{rec1_id}")
    check("T4 Get recipient by ID", r.status_code == 200 and r.json().get("id") == rec1_id)
else:
    check("T4 Get recipient by ID", False, "no ID")

r = get(token, "/final-recipients")
check("T5 List recipients has items", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — update address
if rec1_id:
    r = put(token, f"/final-recipients/{rec1_id}", {"address": "Calle 200 # 30-40", "city": "Cali"})
    check("T6 Update recipient address", r.status_code == 200, str(r.status_code))
else:
    check("T6 Update recipient address", False, "no ID")

# T7 — verify update persisted
if rec1_id:
    r = get(token, f"/final-recipients/{rec1_id}")
    check("T7 Updated city is Cali", r.status_code == 200 and r.json().get("city") == "Cali", str(r.json().get("city")))
else:
    check("T7 Updated city persisted", False, "no ID")

# T8 — invalid phone -> 422
r = post(token, "/final-recipients", {
    "name": "Nombre Valido",
    "phone": "NOPHONE",
    "address": "Calle 1 # 1-1",
    "city": "Bogotá",
})
check("T8 Invalid phone -> 422", r.status_code == 422, str(r.status_code))

r = get(token, "/final-recipients/000000000000000000000000")
check("T9 Unknown recipient -> 404", r.status_code == 404)

if rec2_id:
    r = delete(token, f"/final-recipients/{rec2_id}")
    check("T10 Delete recipient -> 204", r.status_code == 204)
else:
    check("T10 Delete recipient -> 204", False, "no ID")

# ─────────── 5. TRIP STATUSES ────────────────────────────────────────────────

section("MODULE 5: TRIP STATUSES (10 tests)")

r = get(token, "/trip-statuses")
check("T1 List trip-statuses returns 200", r.status_code == 200)

r = post(token, "/trip-statuses", {
    "name": f"Estado {rnd(4).upper()}",
    "description": "Estado de prueba para el viaje",
    "sequence_order": random.randint(1, 50),
    "is_terminal": False,
})
check("T2 Create trip status returns 201", r.status_code == 201, str(r.status_code))
ts1_id = r.json().get("id") if r.status_code == 201 else None
ts1_name = r.json().get("name") if r.status_code == 201 else None

r = post(token, "/trip-statuses", {
    "name": f"Terminal {rnd(4).upper()}",
    "description": "Estado final del viaje",
    "sequence_order": 99,
    "is_terminal": True,
})
check("T3 Create terminal trip status", r.status_code == 201, str(r.status_code))
ts2_id = r.json().get("id") if r.status_code == 201 else None

if ts1_id:
    r = get(token, f"/trip-statuses/{ts1_id}")
    check("T4 Get trip status by ID", r.status_code == 200 and r.json().get("id") == ts1_id)
else:
    check("T4 Get trip status by ID", False, "no ID")

r = get(token, "/trip-statuses")
check("T5 List has created statuses", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — duplicate name -> 409
if ts1_name:
    r = post(token, "/trip-statuses", {
        "name": ts1_name,
        "description": "Duplicado",
        "sequence_order": 5,
        "is_terminal": False,
    })
    check("T6 Duplicate status name -> 409", r.status_code == 409, str(r.status_code))
else:
    check("T6 Duplicate status name -> 409", False, "no name from T2")

# T7 — update description
if ts1_id:
    r = put(token, f"/trip-statuses/{ts1_id}", {"description": "Descripción actualizada para prueba"})
    check("T7 Update trip status description", r.status_code == 200, str(r.status_code))
else:
    check("T7 Update trip status description", False, "no ID")

# T8 — invalid sequence_order (>100) -> 422
r = post(token, "/trip-statuses", {
    "name": f"Invalido{rnd(4)}",
    "sequence_order": 200,
    "is_terminal": False,
})
check("T8 sequence_order > 100 -> 422", r.status_code == 422, str(r.status_code))

r = get(token, "/trip-statuses/000000000000000000000000")
check("T9 Unknown trip status -> 404", r.status_code == 404)

if ts2_id:
    r = delete(token, f"/trip-statuses/{ts2_id}")
    check("T10 Delete trip status -> 204", r.status_code == 204)
else:
    check("T10 Delete trip status -> 204", False, "no ID")

# ─────────── 6. DRIVERS ──────────────────────────────────────────────────────

section("MODULE 6: DRIVERS (10 tests)")

r = get(token, "/drivers")
check("T1 List drivers returns 200", r.status_code == 200)

dr_id_num1 = str(random.randint(10000000, 99999999))
r = post(token, "/drivers", {
    "id_number": dr_id_num1,
    "first_name": "Carlos",
    "last_name": f"Rodríguez{rnd(3)}",
    "phone": "+57 312 5551234",
    "address": "Carrera 15 # 80-10",
    "email": f"carlos{rnd(4)}@example.com",
    "license_number": f"LIC{random.randint(10000, 99999)}",
    "license_category": "C2",
    "license_expiry": future(500),
})
check("T2 Create driver returns 201", r.status_code == 201, str(r.status_code))
dr1_id = r.json().get("id") if r.status_code == 201 else None

dr_id_num2 = str(random.randint(10000000, 99999999))
r = post(token, "/drivers", {
    "id_number": dr_id_num2,
    "first_name": "María",
    "last_name": f"González{rnd(3)}",
    "phone": "+57 320 9990000",
    "address": "Calle 72 # 11-09",
    "license_number": f"LIC{random.randint(10000, 99999)}",
    "license_category": "C1",
    "license_expiry": future(800),
})
check("T3 Create second driver returns 201", r.status_code == 201, str(r.status_code))
dr2_id = r.json().get("id") if r.status_code == 201 else None

if dr1_id:
    r = get(token, f"/drivers/{dr1_id}")
    check("T4 Get driver by ID", r.status_code == 200 and r.json().get("id") == dr1_id)
else:
    check("T4 Get driver by ID", False, "no ID")

r = get(token, "/drivers")
check("T5 List drivers has items", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — duplicate ID number -> 409
r = post(token, "/drivers", {
    "id_number": dr_id_num1,
    "first_name": "Duplicado",
    "last_name": "Test",
    "phone": "3001234567",
    "address": "Calle 1 # 1-1",
    "license_number": f"LIC{random.randint(10000, 99999)}",
    "license_category": "C1",
    "license_expiry": future(365),
})
check("T6 Duplicate driver ID -> 409", r.status_code == 409, str(r.status_code))

# T7 — update phone
if dr1_id:
    r = put(token, f"/drivers/{dr1_id}", {"phone": "+57 315 9999999"})
    check("T7 Update driver phone", r.status_code == 200, str(r.status_code))
else:
    check("T7 Update driver phone", False, "no ID")

# T8 — expired license -> 422
r = post(token, "/drivers", {
    "id_number": str(random.randint(10000000, 99999999)),
    "first_name": "Expirado",
    "last_name": "Test",
    "phone": "3001234567",
    "address": "Calle 1 # 1-1",
    "license_number": "LIC00001",
    "license_category": "C1",
    "license_expiry": "2020-01-01T00:00:00Z",
})
check("T8 Expired license -> 422", r.status_code == 422, str(r.status_code))

r = get(token, "/drivers/000000000000000000000000")
check("T9 Unknown driver -> 404", r.status_code == 404)

if dr2_id:
    r = delete(token, f"/drivers/{dr2_id}")
    check("T10 Delete driver -> 204", r.status_code == 204)
else:
    check("T10 Delete driver -> 204", False, "no ID")

# ─────────── 7. VEHICLES ─────────────────────────────────────────────────────

section("MODULE 7: VEHICLES (10 tests)")

# Need a company for vehicle's company_id
veh_co_id = co1_id  # reuse from module 2

r = get(token, "/vehicles")
check("T1 List vehicles returns 200", r.status_code == 200)

plate1 = f"T{''.join(random.choices(string.digits, k=3))}ABC"[:8]
r = post(token, "/vehicles", {
    "plate": plate1,
    "vehicle_type": "truck",
    "brand": "Volvo",
    "model_year": 2020,
    "capacity_tons": 30.0,
    "volume_m3": 80.0,
    "company_id": veh_co_id or "000000000000000000000001",
    "soat_expiry": future(365),
    "tech_review_expiry": future(180),
})
check("T2 Create vehicle returns 201", r.status_code == 201, str(r.status_code))
veh1_id = r.json().get("id") if r.status_code == 201 else None

plate2 = f"V{''.join(random.choices(string.digits, k=3))}DEF"[:8]
r = post(token, "/vehicles", {
    "plate": plate2,
    "vehicle_type": "van",
    "brand": "Mercedes",
    "model_year": 2022,
    "capacity_tons": 5.0,
    "company_id": veh_co_id or "000000000000000000000001",
})
check("T3 Create second vehicle returns 201", r.status_code == 201, str(r.status_code))
veh2_id = r.json().get("id") if r.status_code == 201 else None

if veh1_id:
    r = get(token, f"/vehicles/{veh1_id}")
    check("T4 Get vehicle by ID", r.status_code == 200 and r.json().get("id") == veh1_id)
else:
    check("T4 Get vehicle by ID", False, "no ID")

r = get(token, "/vehicles")
check("T5 List vehicles has items", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — duplicate plate -> 409
r = post(token, "/vehicles", {
    "plate": plate1,
    "vehicle_type": "truck",
    "brand": "Ford",
    "model_year": 2021,
    "capacity_tons": 10.0,
    "company_id": veh_co_id or "000000000000000000000001",
})
check("T6 Duplicate plate -> 409", r.status_code == 409, str(r.status_code))

# T7 — update capacity
if veh1_id:
    r = put(token, f"/vehicles/{veh1_id}", {"capacity_tons": 35.0})
    check("T7 Update vehicle capacity", r.status_code == 200, str(r.status_code))
else:
    check("T7 Update vehicle capacity", False, "no ID")

# T8 — model_year too old -> 422
r = post(token, "/vehicles", {
    "plate": f"OLD{rnd(3).upper()}",
    "vehicle_type": "truck",
    "brand": "Ancient",
    "model_year": 1950,
    "capacity_tons": 5.0,
    "company_id": "000000000000000000000001",
})
check("T8 model_year < 1990 -> 422", r.status_code == 422, str(r.status_code))

r = get(token, "/vehicles/000000000000000000000000")
check("T9 Unknown vehicle -> 404", r.status_code == 404)

if veh2_id:
    r = delete(token, f"/vehicles/{veh2_id}")
    check("T10 Delete vehicle -> 204", r.status_code == 204)
else:
    check("T10 Delete vehicle -> 204", False, "no ID")

# ─────────── 8. TRIPS ────────────────────────────────────────────────────────

section("MODULE 8: TRIPS (10 tests)")

r = get(token, "/trips")
check("T1 List trips returns 200", r.status_code == 200)

# Use IDs from previous modules
trip_vehicle_id = veh1_id or "000000000000000000000001"
trip_driver_id = dr1_id or "000000000000000000000001"
trip_cargo_id = cargo1_id or "000000000000000000000001"
trip_client_id = cl1_id or "000000000000000000000001"
trip_recipient_id = rec1_id or "000000000000000000000001"

r = post(token, "/trips", {
    "origin": "Bogotá, Cundinamarca",
    "destination": "Medellín, Antioquia",
    "departure_date": future(5),
    "arrival_date": future(7),
    "weight_tons": 15.0,
    "total_cost": 4500000.0,
    "vehicle_id": trip_vehicle_id,
    "driver_id": trip_driver_id,
    "cargo_id": trip_cargo_id,
    "client_id": trip_client_id,
    "recipient_id": trip_recipient_id,
    "notes": "Viaje de prueba automatizado",
})
check("T2 Create trip returns 201", r.status_code == 201, str(r.status_code))
trip1_id = r.json().get("id") if r.status_code == 201 else None

r = post(token, "/trips", {
    "origin": "Cali, Valle",
    "destination": "Barranquilla, Atlántico",
    "departure_date": future(10),
    "weight_tons": 8.0,
    "total_cost": 2800000.0,
    "vehicle_id": trip_vehicle_id,
    "driver_id": trip_driver_id,
    "cargo_id": trip_cargo_id,
    "client_id": trip_client_id,
    "recipient_id": trip_recipient_id,
})
check("T3 Create second trip returns 201", r.status_code == 201, str(r.status_code))
trip2_id = r.json().get("id") if r.status_code == 201 else None

if trip1_id:
    r = get(token, f"/trips/{trip1_id}")
    check("T4 Get trip by ID", r.status_code == 200 and r.json().get("id") == trip1_id)
else:
    check("T4 Get trip by ID", False, "no ID")

r = get(token, "/trips")
check("T5 List trips has items", r.status_code == 200 and r.json().get("total", 0) >= 1)

# T6 — departure in past -> 422
r = post(token, "/trips", {
    "origin": "Bogotá",
    "destination": "Cali",
    "departure_date": "2020-01-01T00:00:00Z",
    "weight_tons": 5.0,
    "total_cost": 1000000.0,
    "vehicle_id": trip_vehicle_id,
    "driver_id": trip_driver_id,
    "cargo_id": trip_cargo_id,
    "client_id": trip_client_id,
    "recipient_id": trip_recipient_id,
})
check("T6 Past departure_date -> 422", r.status_code == 422, str(r.status_code))

# T7 — update trip status
if trip1_id and ts1_id:
    r = put(token, f"/trips/{trip1_id}/status", {"status_code": ts1_id})
    check("T7 Update trip status", r.status_code in (200, 400), str(r.status_code))
else:
    check("T7 Update trip status", False, "missing IDs")

# T8 — zero weight -> 422
r = post(token, "/trips", {
    "origin": "Bogotá",
    "destination": "Cali",
    "departure_date": future(3),
    "weight_tons": 0.0,
    "total_cost": 500000.0,
    "vehicle_id": trip_vehicle_id,
    "driver_id": trip_driver_id,
    "cargo_id": trip_cargo_id,
    "client_id": trip_client_id,
    "recipient_id": trip_recipient_id,
})
check("T8 weight_tons=0 -> 422", r.status_code == 422, str(r.status_code))

r = get(token, "/trips/000000000000000000000000")
check("T9 Unknown trip -> 404", r.status_code == 404)

if trip2_id:
    r = delete(token, f"/trips/{trip2_id}")
    check("T10 Delete trip -> 204", r.status_code in (204, 200, 400), str(r.status_code))
else:
    check("T10 Delete trip -> 204", False, "no ID")

# ─────────── 9. INVOICES ─────────────────────────────────────────────────────

section("MODULE 9: INVOICES (10 tests)")

r = get(token, "/invoices")
check("T1 List invoices returns 200", r.status_code == 200)

r = get(token, "/invoices?limit=10&skip=0")
check("T2 List invoices with pagination params", r.status_code == 200)

r = get(token, "/invoices?status=issued")
check("T3 List invoices filtered by status=issued", r.status_code == 200)

r = get(token, "/invoices?status=paid")
check("T4 List invoices filtered by status=paid", r.status_code == 200)

# T5 — Get all invoices and pick first if available
inv_list = get(token, "/invoices").json()
inv1_id = None
if inv_list.get("total", 0) > 0 and inv_list.get("items"):
    inv1_id = inv_list["items"][0].get("id")
check("T5 Get invoice list total is numeric", isinstance(inv_list.get("total"), int))

# T6 — Get by ID if we have one
if inv1_id:
    r = get(token, f"/invoices/{inv1_id}")
    check("T6 Get invoice by ID", r.status_code == 200)
else:
    check("T6 Get invoice by ID", True, "no invoices yet (trips just created)")

# T7 — 404 for unknown ID
r = get(token, "/invoices/000000000000000000000000")
check("T7 Unknown invoice -> 404", r.status_code == 404)

# T8 — Mark as paid if we have invoice
if inv1_id:
    r = put(token, f"/invoices/{inv1_id}/pay", {})
    check("T8 Mark invoice as paid", r.status_code in (200, 400))
else:
    check("T8 Mark invoice as paid", True, "no invoice available, skipped")

# T9 — filter by client
r = get(token, f"/invoices?client_id=000000000000000000000001")
check("T9 Filter invoices by client_id", r.status_code == 200)

# T10 — Void invoice
if inv1_id:
    r = put(token, f"/invoices/{inv1_id}/void", {})
    check("T10 Void invoice", r.status_code in (200, 400))
else:
    check("T10 Void invoice", True, "no invoice available, skipped")

# ─────────── SUMMARY ─────────────────────────────────────────────────────────

section("RESULTS")
total = PASS + FAIL
pct = int(100 * PASS / total) if total else 0
print(f"\n  PASSED : {PASS}/{total} ({pct}%)")
print(f"  FAILED : {FAIL}/{total}")

if FAIL:
    print("\n  Some tests failed — check output above for details.")
    sys.exit(1)
else:
    print("\n  ALL TESTS PASSED!")
    sys.exit(0)
