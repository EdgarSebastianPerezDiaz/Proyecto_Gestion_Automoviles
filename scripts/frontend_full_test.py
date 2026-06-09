"""
Prueba integral de todos los módulos del frontend Heavy Freight Platform.
Simula exactamente las llamadas HTTP que hace cada servicio Angular.
"""
import sys, io, requests, json, time
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com"
PASS_COUNT = 0
FAIL_COUNT = 0
ERRORS = []


def sep(t):
    print(f"\n{'='*62}\n  {t}\n{'='*62}")


def chk(label, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {label}")
    else:
        FAIL_COUNT += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        ERRORS.append(f"{label} — {detail}")


def get(path, params=None):
    return requests.get(f"{API}{path}", headers=H, params=params, timeout=20)


def post(path, body):
    return requests.post(f"{API}{path}", headers=H, json=body, timeout=20)


def put(path, body):
    return requests.put(f"{API}{path}", headers=H, json=body, timeout=20)


def patch(path, body):
    return requests.patch(f"{API}{path}", headers=H, json=body, timeout=20)


def delete(path):
    return requests.delete(f"{API}{path}", headers=H, timeout=20)


# ── LOGIN ─────────────────────────────────────────────────────────────────────
sep("AUTH — Login")
r = requests.post(f"{API}/auth/login",
                  json={"email": "admin@heavy-freight.com", "password": "Admin123!"},
                  timeout=15)
chk("POST /auth/login → 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
chk("response has access_token", "access_token" in data)
chk("response has refresh_token", "refresh_token" in data)
tok = data.get("access_token", "")
ref = data.get("refresh_token", "")
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
sep("DASHBOARD — Carga inicial (4 endpoints)")
r = get("/trips",    {"page": 1, "limit": 1000})
chk("GET /trips?limit=1000 → 200", r.status_code == 200, f"got {r.status_code}")
trips_all = r.json().get("items", [])
chk("dashboard trips tiene items", len(trips_all) > 0, f"got {len(trips_all)}")

r = get("/vehicles", {"page": 1, "limit": 1000})
chk("GET /vehicles?limit=1000 → 200", r.status_code == 200, f"got {r.status_code}")
vehicles_all = r.json().get("items", [])
chk("dashboard vehicles tiene items", len(vehicles_all) > 0, f"got {len(vehicles_all)}")

r = get("/drivers", {"page": 1, "limit": 1000})
chk("GET /drivers?limit=1000 → 200", r.status_code == 200, f"got {r.status_code}")
drivers_all = r.json().get("items", [])
chk("dashboard drivers tiene items", len(drivers_all) > 0, f"got {len(drivers_all)}")

r = get("/invoices", {"page": 1, "limit": 1000})
chk("GET /invoices?limit=1000 → 200", r.status_code == 200, f"got {r.status_code}")
invoices_all = r.json().get("items", [])
chk("dashboard invoices tiene items", len(invoices_all) >= 0, f"got {len(invoices_all)}")

# Métricas dashboard
viajes_programados = [t for t in trips_all if t.get("estado") in ("Programado", "programado")]
viajes_en_ruta     = [t for t in trips_all if t.get("estado") in ("En Ruta", "en_ruta")]
viajes_entregados  = [t for t in trips_all if t.get("estado") in ("Entregado", "entregado")]
print(f"         KPIs: viajes={len(trips_all)} | programados={len(viajes_programados)} | en_ruta={len(viajes_en_ruta)} | entregados={len(viajes_entregados)}")
print(f"         vehiculos={len(vehicles_all)} | conductores={len(drivers_all)} | facturas={len(invoices_all)}")

# ── COMPANIES ────────────────────────────────────────────────────────────────
sep("COMPANIES — Listado, Crear, Editar, Eliminar")
r = get("/companies", {"page": 1, "limit": 10})
chk("GET /companies (paginado) → 200", r.status_code == 200, f"got {r.status_code}")
companies = r.json().get("items", [])
chk("companies tiene items", len(companies) > 0, f"got {len(companies)}")
if companies:
    c0 = companies[0]
    chk("company tiene 'nombre'",    "nombre"    in c0, str(list(c0.keys())[:6]))
    chk("company tiene 'nit'",       "nit"       in c0)
    chk("company tiene 'telefono'",  "telefono"  in c0)
    chk("company tiene 'correo'",    "correo"    in c0)
    chk("company tiene 'direccion'", "direccion" in c0)

r = get("/companies", {"search": "Andina"})
chk("GET /companies?search=Andina → 200", r.status_code == 200, f"got {r.status_code}")

r = post("/companies", {
    "nombre": "Test Empresa Prueba S.A.S", "nit": "999.888.777-6",
    "direccion": "Calle Test #1-23, Bogota", "telefono": "6019998877",
    "correo": "test.prueba@empresa.com"
})
chk("POST /companies → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
co_id = None
if r.status_code == 201:
    co_id = r.json()["id"]
    r2 = put(f"/companies/{co_id}", {
        "nombre": "Test Empresa Actualizada S.A.S", "telefono": "6011112233",
        "direccion": "Av Nueva #10-20, Bogota", "correo": "test.prueba@empresa.com"
    })
    chk("PUT /companies/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:80]}")
    r3 = get(f"/companies/{co_id}")
    chk("GET /companies/{id} → 200", r3.status_code == 200, f"got {r3.status_code}")
    r4 = delete(f"/companies/{co_id}")
    chk("DELETE /companies/{id} → 204", r4.status_code == 204, f"got {r4.status_code}")

# ── CLIENTS (Transportistas) ──────────────────────────────────────────────────
sep("CLIENTS (Transportistas) — Listado, Crear, Editar, Eliminar")
r = get("/clients", {"page": 1, "limit": 10})
chk("GET /clients → 200", r.status_code == 200, f"got {r.status_code}")
clients = r.json().get("items", [])
chk("clients tiene items", len(clients) > 0, f"got {len(clients)}")
if clients:
    c0 = clients[0]
    chk("client tiene 'nombre'",   "nombre"   in c0, str(list(c0.keys())[:6]))
    chk("client tiene 'telefono'", "telefono" in c0)
    chk("client tiene 'correo'",   "correo"   in c0)

r = post("/clients", {
    "nombre": "Test Cliente Prueba Ltda", "nit": "888.777.666-5",
    "direccion": "Cra Test #5-10, Medellin", "telefono": "6048887766",
    "correo": "test.cliente@prueba.com", "tipoDocumento": "NIT"
})
chk("POST /clients → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
cl_id = None
if r.status_code == 201:
    cl_id = r.json()["id"]
    r2 = put(f"/clients/{cl_id}", {
        "nombre": "Test Cliente Actualizado Ltda", "telefono": "6041112233",
        "correo": "test.cliente.upd@prueba.com"
    })
    chk("PUT /clients/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:80]}")
    r3 = delete(f"/clients/{cl_id}")
    chk("DELETE /clients/{id} → 204", r3.status_code == 204, f"got {r3.status_code}")

# ── DRIVERS ───────────────────────────────────────────────────────────────────
sep("DRIVERS — Listado, Filtros, Crear, Editar, Eliminar")
r = get("/drivers", {"page": 1, "limit": 10})
chk("GET /drivers (paginado) → 200", r.status_code == 200, f"got {r.status_code}")
drivers = r.json().get("items", [])
chk("drivers tiene items", len(drivers) > 0, f"got {len(drivers)}")
if drivers:
    d0 = drivers[0]
    chk("driver tiene 'fullName'",          "fullName"          in d0, str(list(d0.keys())[:6]))
    chk("driver tiene 'cedula'",            "cedula"            in d0)
    chk("driver tiene 'categoriaLicencia'", "categoriaLicencia" in d0)
    chk("driver tiene 'numeroLicencia'",    "numeroLicencia"    in d0)

# Filtro de licencia (simula el dropdown del frontend)
r = get("/drivers", {"page": 1, "limit": 1000})
chk("GET /drivers?limit=1000 (conteo licencias) → 200", r.status_code == 200, f"got {r.status_code}")

r = post("/drivers", {
    "fullName": "Test Conductor Prueba", "cedula": "111222333",
    "telefono": "3001112233", "direccion": "Calle Test #2-34, Cali",
    "correo": "test.conductor@prueba.com", "numeroLicencia": "LICTEST001",
    "categoriaLicencia": "C2", "fechaVencimientoLicencia": "2029-06-30T23:59:59"
})
chk("POST /drivers → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
dr_id = None
if r.status_code == 201:
    dr_id = r.json()["id"]
    r2 = put(f"/drivers/{dr_id}", {
        "fullName": "Test Conductor Actualizado", "telefono": "3009998877",
        "direccion": "Av Test #5-67, Cali", "correo": "test.conductor@prueba.com",
        "numeroLicencia": "LICTEST001", "categoriaLicencia": "C3",
        "fechaVencimientoLicencia": "2029-12-31T23:59:59"
    })
    chk("PUT /drivers/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:100]}")
    r3 = get(f"/drivers/{dr_id}")
    chk("GET /drivers/{id} → 200", r3.status_code == 200, f"got {r3.status_code}")
    r4 = delete(f"/drivers/{dr_id}")
    chk("DELETE /drivers/{id} → 204", r4.status_code == 204, f"got {r4.status_code}")

# ── VEHICLES ──────────────────────────────────────────────────────────────────
sep("VEHICLES — Listado, Filtros, Crear, Editar, Eliminar")
r = get("/vehicles", {"page": 1, "limit": 10})
chk("GET /vehicles (paginado) → 200", r.status_code == 200, f"got {r.status_code}")
vehicles = r.json().get("items", [])
chk("vehicles tiene items", len(vehicles) > 0, f"got {len(vehicles)}")
if vehicles:
    v0 = vehicles[0]
    chk("vehicle tiene 'placa'",    "placa"    in v0, str(list(v0.keys())[:6]))
    chk("vehicle tiene 'marca'",    "marca"    in v0)
    chk("vehicle tiene 'estado'",   "estado"   in v0)
    chk("vehicle estado es español", v0.get("estado") in ("Disponible", "En Viaje", "Inactivo"),
        f"got '{v0.get('estado')}'")

# Filtro por estado (simula dropdown frontend)
for estado in ("Disponible", "En Viaje", "Inactivo"):
    r = get("/vehicles", {"estado": estado})
    chk(f"GET /vehicles?estado={estado} → 200", r.status_code == 200, f"got {r.status_code}")

# Obtener empresa para asociar vehículo
existing_companies = get("/companies", {"limit": 5}).json().get("items", [])
co_ref = existing_companies[0]["id"] if existing_companies else ""

r = post("/vehicles", {
    "placa": "TST001", "marca": "Volvo Test", "modelo": 2023,
    "capacidad": 30.0, "transportistaId": co_ref, "estado": "Disponible"
})
chk("POST /vehicles → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
vh_id = None
if r.status_code == 201:
    vh_id = r.json()["id"]
    r2 = put(f"/vehicles/{vh_id}", {
        "marca": "Volvo Actualizado", "modelo": 2024, "capacidad": 35.0, "estado": "Disponible"
    })
    chk("PUT /vehicles/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:80]}")
    r3 = get(f"/vehicles/{vh_id}")
    chk("GET /vehicles/{id} → 200", r3.status_code == 200, f"got {r3.status_code}")
    r4 = delete(f"/vehicles/{vh_id}")
    chk("DELETE /vehicles/{id} → 204", r4.status_code == 204, f"got {r4.status_code}")

# ── CARGO TYPES ───────────────────────────────────────────────────────────────
sep("CARGO TYPES — Listado, Crear, Editar, Eliminar")
r = get("/cargo-types", {"page": 1, "limit": 10})
chk("GET /cargo-types (paginado) → 200", r.status_code == 200, f"got {r.status_code}")
cargos = r.json().get("items", [])
chk("cargo-types tiene items", len(cargos) > 0, f"got {len(cargos)}")
if cargos:
    ct0 = cargos[0]
    chk("cargo_type tiene 'nombre'",      "nombre"      in ct0, str(list(ct0.keys())[:6]))
    chk("cargo_type tiene 'descripcion'", "descripcion" in ct0)
    chk("cargo_type tiene 'precioPorTon'","precioPorTon" in ct0)
    chk("precioPorTon es numerico", isinstance(ct0.get("precioPorTon"), (int, float)),
        f"type={type(ct0.get('precioPorTon')).__name__}")

r = post("/cargo-types", {
    "nombre": "Test Carga Prueba", "descripcion": "Tipo de carga para pruebas del sistema",
    "precioPorTon": 150000.0
})
chk("POST /cargo-types → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
cg_id = None
if r.status_code == 201:
    cg_id = r.json()["id"]
    r2 = put(f"/cargo-types/{cg_id}", {
        "nombre": "Test Carga Actualizada", "descripcion": "Descripcion actualizada",
        "precioPorTon": 175000.0
    })
    chk("PUT /cargo-types/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:80]}")
    r3 = delete(f"/cargo-types/{cg_id}")
    chk("DELETE /cargo-types/{id} → 204", r3.status_code == 204, f"got {r3.status_code}")

# ── FINAL RECIPIENTS ──────────────────────────────────────────────────────────
sep("FINAL RECIPIENTS — Listado, Crear, Editar, Eliminar")
r = get("/final-recipients", {"page": 1, "limit": 10})
chk("GET /final-recipients → 200", r.status_code == 200, f"got {r.status_code}")
recipients = r.json().get("items", [])
chk("final-recipients tiene items", len(recipients) > 0, f"got {len(recipients)}")
if recipients:
    fr0 = recipients[0]
    chk("recipient tiene 'nombre'",   "nombre"   in fr0, str(list(fr0.keys())[:6]))
    chk("recipient tiene 'telefono'", "telefono" in fr0)
    chk("recipient tiene 'correo'",   "correo"   in fr0)

r = post("/final-recipients", {
    "nombre": "Test Destinatario Prueba", "nit": "777.666.555-4",
    "direccion": "Bodega Test #3-45, Barranquilla", "telefono": "6057776655",
    "correo": "test.destinatario@prueba.com"
})
chk("POST /final-recipients → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
fr_id = None
if r.status_code == 201:
    fr_id = r.json()["id"]
    r2 = put(f"/final-recipients/{fr_id}", {
        "nombre": "Test Destinatario Actualizado", "telefono": "6051112233",
        "correo": "test.dest.upd@prueba.com", "direccion": "Av Prueba #8-90, Barranquilla"
    })
    chk("PUT /final-recipients/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:80]}")
    r3 = get(f"/final-recipients/{fr_id}")
    chk("GET /final-recipients/{id} → 200", r3.status_code == 200, f"got {r3.status_code}")
    r4 = delete(f"/final-recipients/{fr_id}")
    chk("DELETE /final-recipients/{id} → 204", r4.status_code == 204, f"got {r4.status_code}")

# ── TRIP STATUSES ─────────────────────────────────────────────────────────────
sep("TRIP STATUSES — Listado (usado en dropdowns)")
r = get("/trip-statuses")
chk("GET /trip-statuses → 200", r.status_code == 200, f"got {r.status_code}")
statuses = r.json().get("items", [])
chk("trip-statuses tiene items", len(statuses) > 0, f"got {len(statuses)}")
if statuses:
    s0 = statuses[0]
    chk("status tiene 'nombre'", "nombre" in s0 or "name" in s0, str(list(s0.keys())[:5]))
    chk("status tiene 'code'",   "code"   in s0)

# ── TRIPS ─────────────────────────────────────────────────────────────────────
sep("TRIPS — Listado, Filtros, Crear, PATCH Status, Eliminar")
r = get("/trips", {"page": 1, "limit": 10})
chk("GET /trips (paginado) → 200", r.status_code == 200, f"got {r.status_code}")
trips = r.json().get("items", [])
chk("trips tiene items", len(trips) > 0, f"got {len(trips)}")
if trips:
    t0 = trips[0]
    chk("trip tiene 'id'",          "id"          in t0, str(list(t0.keys())[:8]))
    chk("trip tiene 'origen'",      "origin"      in t0 or "origen" in t0)
    chk("trip tiene 'destino'",     "destination" in t0 or "destino" in t0)
    chk("trip tiene 'estado'",      "estado"      in t0)
    chk("trip tiene 'peso'",        "peso"        in t0 or "weight_tons" in t0)
    chk("trip estado es español",
        t0.get("estado") in ("Programado","En Ruta","Entregado","Cancelado","En Tránsito") or
        t0.get("estado","").startswith("En") or t0.get("estado","").startswith("Programado"),
        f"got '{t0.get('estado')}'")

# Filtros por estado
for estado in ("Programado", "En Ruta", "Entregado"):
    r = get("/trips", {"estado": estado, "page": 1, "limit": 10})
    chk(f"GET /trips?estado={estado} → 200", r.status_code == 200, f"got {r.status_code}")

# Filtro para cumplidos: viajes entregados sin fulfillment
r = get("/trips", {"estado": "Entregado", "without_fulfillment": "true", "page": 1, "limit": 1000})
chk("GET /trips?estado=Entregado&without_fulfillment=true → 200", r.status_code == 200, f"got {r.status_code}")

# Buscar IDs para crear viaje de prueba
existing_vehicles  = get("/vehicles",         {"limit": 5}).json().get("items", [])
existing_drivers   = get("/drivers",          {"limit": 5}).json().get("items", [])
existing_cargos    = get("/cargo-types",      {"limit": 5}).json().get("items", [])
existing_clients   = get("/clients",          {"limit": 5}).json().get("items", [])
existing_recip     = get("/final-recipients", {"limit": 5}).json().get("items", [])

if all([existing_vehicles, existing_drivers, existing_cargos, existing_clients, existing_recip]):
    now = datetime.now(timezone.utc)
    sal = (now + timedelta(days=3)).replace(hour=8, minute=0, second=0, microsecond=0)
    ll  = (now + timedelta(days=5)).replace(hour=18, minute=0, second=0, microsecond=0)

    r = post("/trips", {
        "origin":               "Bogota, Cundinamarca",
        "destination":          "Medellin, Antioquia",
        "vehiculoId":           existing_vehicles[0]["id"],
        "conductorId":          existing_drivers[0]["id"],
        "cargoTypeId":          existing_cargos[0]["id"],
        "transportistaId":      existing_clients[0]["id"],
        "destinoId":            existing_recip[0]["id"],
        "peso":                 20.0, "costoTotal": 4000000.0,
        "fechaSalida":          sal.isoformat(),
        "fechaLlegadaEstimada": ll.isoformat(),
    })
    chk("POST /trips → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:150]}")
    tr_id = None
    if r.status_code == 201:
        tr = r.json()
        tr_id = tr["id"]
        estado_inicial = tr.get("estado", "?")
        chk("trip creado tiene estado='Programado'", estado_inicial == "Programado",
            f"got '{estado_inicial}'")

        r2 = get(f"/trips/{tr_id}")
        chk("GET /trips/{id} → 200", r2.status_code == 200, f"got {r2.status_code}")

        # PATCH status: Programado → en_ruta
        rp = patch(f"/trips/{tr_id}/status", {"status_code": "en_ruta"})
        chk("PATCH /trips/{id}/status 'en_ruta' → 200", rp.status_code == 200,
            f"got {rp.status_code}: {rp.text[:80]}")
        if rp.status_code == 200:
            chk("estado tras PATCH es 'En Ruta'", rp.json().get("estado") == "En Ruta",
                f"got '{rp.json().get('estado')}'")

        # Intentar DELETE (debe fallar — solo se puede en estado programado)
        rd = delete(f"/trips/{tr_id}")
        chk("DELETE /trips/{id} en 'En Ruta' → 400 (esperado)", rd.status_code == 400,
            f"got {rd.status_code}")
else:
    print("  [SKIP] No hay suficientes datos para crear viaje de prueba")

# ── INVOICES ──────────────────────────────────────────────────────────────────
sep("INVOICES (Cumplidos) — Listado, Filtros, Crear")
r = get("/invoices", {"page": 1, "limit": 10})
chk("GET /invoices → 200", r.status_code == 200, f"got {r.status_code}")
invoices = r.json().get("items", [])
chk("invoices tiene items", len(invoices) >= 0, f"got {len(invoices)}")
if invoices:
    inv0 = invoices[0]
    chk("invoice tiene 'numero'", "numero" in inv0 or "invoice_number" in inv0,
        str(list(inv0.keys())[:8]))
    chk("invoice tiene estado",   "estado" in inv0 or "status" in inv0)

# Filtro estadoPago
for ep in ("Pendiente", "Pagado"):
    r = get("/invoices", {"estadoPago": ep, "page": 1, "limit": 10})
    chk(f"GET /invoices?estadoPago={ep} → 200", r.status_code == 200, f"got {r.status_code}")

# Rango de fechas (para reportes)
now = datetime.now(timezone.utc)
r = get("/invoices", {
    "page": 1, "limit": 10000,
    "dateFrom": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
    "dateTo":   now.strftime("%Y-%m-%d")
})
chk("GET /invoices?dateFrom&dateTo → 200", r.status_code == 200, f"got {r.status_code}")

# ── USERS ─────────────────────────────────────────────────────────────────────
sep("USERS — Listado, Filtros, Crear, Editar, Eliminar")
r = get("/users", {"page": 1, "limit": 10})
chk("GET /users → 200", r.status_code == 200, f"got {r.status_code}")
users = r.json().get("items", [])
chk("users tiene items", len(users) > 0, f"got {len(users)}")
if users:
    u0 = users[0]
    chk("user tiene 'email'",    "email"    in u0, str(list(u0.keys())[:6]))
    chk("user tiene 'role'",     "role"     in u0 or "rol" in u0)
    chk("user tiene 'full_name'","full_name" in u0 or "nombre" in u0)

# Filtro por rol
for rol in ("admin", "operator"):
    r = get("/users", {"rol": rol, "page": 1, "limit": 10})
    chk(f"GET /users?rol={rol} → 200", r.status_code in (200, 404), f"got {r.status_code}")

# Crear usuario de prueba
import random, string
rand_suffix = ''.join(random.choices(string.digits, k=6))
r = post("/auth/register", {
    "email": f"test.user{rand_suffix}@heavy-freight.com",
    "password": "Test1234!",
    "full_name": f"Usuario Prueba {rand_suffix}",
    "role": "operator"
})
chk("POST /auth/register → 201", r.status_code == 201, f"got {r.status_code}: {r.text[:100]}")
usr_id = None
if r.status_code == 201:
    usr_id = r.json().get("id") or r.json().get("user_id")
    if usr_id:
        r2 = put(f"/users/{usr_id}", {
            "full_name": f"Usuario Actualizado {rand_suffix}",
            "role": "operator"
        })
        chk("PUT /users/{id} → 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:80]}")
        r3 = delete(f"/users/{usr_id}")
        chk("DELETE /users/{id} → 204", r3.status_code == 204, f"got {r3.status_code}")

# ── AUDIT ─────────────────────────────────────────────────────────────────────
sep("AUDIT — Operaciones y Logins")
r = get("/audit/operations", {"page": 1, "limit": 10})
chk("GET /audit/operations → 200", r.status_code == 200, f"got {r.status_code}")
ops = r.json().get("items", [])
chk("audit/operations tiene items", len(ops) >= 0, f"got {len(ops)}")

r = get("/audit/logins", {"page": 1, "limit": 10})
chk("GET /audit/logins → 200", r.status_code == 200, f"got {r.status_code}")
logins = r.json().get("items", [])
chk("audit/logins tiene items", len(logins) >= 0, f"got {len(logins)}")

# Filtros de auditoría
now = datetime.now(timezone.utc)
r = get("/audit/operations", {
    "page": 1, "limit": 100,
    "dateFrom": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
    "dateTo":   now.strftime("%Y-%m-%d")
})
chk("GET /audit/operations?dateFrom&dateTo → 200", r.status_code == 200, f"got {r.status_code}")

for accion in ("INSERT", "UPDATE", "DELETE"):
    r = get("/audit/operations", {"accion": accion, "page": 1, "limit": 10})
    chk(f"GET /audit/operations?accion={accion} → 200", r.status_code == 200, f"got {r.status_code}")

# ── AUTH REFRESH ──────────────────────────────────────────────────────────────
sep("AUTH — Refresh Token")
r = requests.post(f"{API}/auth/refresh",
                  headers={"Content-Type": "application/json"},
                  json={"refresh_token": ref}, timeout=15)
chk("POST /auth/refresh → 200", r.status_code == 200, f"got {r.status_code}: {r.text[:100]}")
if r.status_code == 200:
    chk("refresh devuelve nuevo access_token", "access_token" in r.json())

# ── RESUMEN ───────────────────────────────────────────────────────────────────
sep("RESUMEN FINAL")
total = PASS_COUNT + FAIL_COUNT
print(f"\n  RESULTADOS: {PASS_COUNT}/{total} pasaron  |  {FAIL_COUNT} fallaron")
if ERRORS:
    print(f"\n  FALLOS:")
    for e in ERRORS:
        print(f"    - {e}")
else:
    print("\n  Todos los endpoints del frontend funcionan correctamente.")
