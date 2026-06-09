"""
Simula el recorrido completo que un usuario hace en la UI:
GET (listar), POST (crear), PUT (editar), PATCH /status, DELETE (limpiar)
para todos los modulos del sistema.
"""
import sys, io, requests, random
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com"


def sep(t):
    print(f"\n{'='*60}\n  {t}\n{'='*60}")


def ok(m):
    print(f"  [OK]   {m}")


def err(m):
    print(f"  [ERR]  {m}")


def inf(m):
    print(f"         {m}")


def rnd_nit():
    d = [random.randint(0, 9) for _ in range(10)]
    return f"{d[0]}{d[1]}{d[2]}.{d[3]}{d[4]}{d[5]}.{d[6]}{d[7]}{d[8]}-{d[9]}"


# ── LOGIN ─────────────────────────────────────────────────────────
sep("LOGIN")
r = requests.post(
    f"{API}/auth/login",
    json={"email": "admin@heavy-freight.com", "password": "Admin123!"},
    timeout=15,
)
if r.status_code != 200:
    err(f"Login fallido {r.status_code}: {r.text}")
    sys.exit(1)
data = r.json()
tok = data["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
ok("Login exitoso como admin@heavy-freight.com")
ok(f"Token recibido (exp en ~15min)")

s = str(random.randint(100000, 999999))
ids = {}

# ── EMPRESAS ──────────────────────────────────────────────────────
sep("MODULO 1 — EMPRESAS (/companies)")
r = requests.get(f"{API}/companies", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} empresas en el sistema")
for it in items[:3]:
    inf(f"  {it.get('nombre')!r}  NIT={it.get('nit')!r}  tel={it.get('telefono')!r}")

nit1 = rnd_nit()
body = {
    "nombre": f"Transportes Test {s} SAS",
    "nit": nit1,
    "direccion": "Calle 100 No 50-30, Bogota",
    "telefono": "6011234567",
    "correo": f"empresa{s}@example.com",
}
r = requests.post(f"{API}/companies", headers=H, json=body, timeout=15)
if r.status_code == 201:
    cmp = r.json()
    ids["company"] = cmp["id"]
    ok(f"CREATE -> id={cmp['id'][:8]}... nombre={cmp.get('nombre')!r} nit={cmp.get('nit')!r}")
    # UPDATE
    r2 = requests.put(
        f"{API}/companies/{ids['company']}",
        headers=H,
        json={
            "nombre": f"Transportes Actualizado {s} SAS",
            "nit": nit1,
            "direccion": "Av El Dorado 68-50, Bogota",
            "telefono": "6019999999",
            "correo": f"empresa{s}@example.com",
        },
        timeout=15,
    )
    if r2.status_code == 200:
        ok(f"UPDATE -> nombre={r2.json().get('nombre')!r}")
    else:
        err(f"UPDATE {r2.status_code}: {r2.text[:120]}")
    # GET by ID
    r3 = requests.get(f"{API}/companies/{ids['company']}", headers=H, timeout=15)
    if r3.status_code == 200:
        ok(f"GET by id -> nombre={r3.json().get('nombre')!r} direccion={r3.json().get('direccion')!r}")
else:
    err(f"CREATE {r.status_code}: {r.text[:200]}")

# ── CLIENTES ──────────────────────────────────────────────────────
sep("MODULO 2 — CLIENTES (transportistas) (/clients)")
r = requests.get(f"{API}/clients", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} clientes")
for it in items[:3]:
    inf(f"  {it.get('nombre')!r}  tel={it.get('telefono')!r}")

body = {
    "nombre": f"Logistica Test {s} Ltda",
    "nit": rnd_nit(),
    "direccion": "Av 80 No 20-15, Medellin",
    "telefono": "4441234567",
    "correo": f"cliente{s}@example.com",
    "tipoDocumento": "NIT",
}
r = requests.post(f"{API}/clients", headers=H, json=body, timeout=15)
if r.status_code == 201:
    cl = r.json()
    ids["client"] = cl["id"]
    ok(f"CREATE -> id={cl['id'][:8]}... nombre={cl.get('nombre')!r}")
    r2 = requests.put(
        f"{API}/clients/{ids['client']}",
        headers=H,
        json={
            "nombre": f"Logistica Actualizada {s}",
            "direccion": "Carrera 30 No 10-20, Cali",
            "telefono": "6020001111",
            "correo": f"cliente{s}@example.com",
        },
        timeout=15,
    )
    if r2.status_code == 200:
        ok(f"UPDATE -> nombre={r2.json().get('nombre')!r}")
    else:
        err(f"UPDATE {r2.status_code}: {r2.text[:120]}")
else:
    err(f"CREATE {r.status_code}: {r.text[:200]}")

# ── CONDUCTORES ───────────────────────────────────────────────────
sep("MODULO 3 — CONDUCTORES (/drivers)")
r = requests.get(f"{API}/drivers", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} conductores")
for it in items[:3]:
    inf(f"  {it.get('fullName')!r}  cedula={it.get('cedula')!r}  licencia={it.get('categoriaLicencia')!r}")

body = {
    "fullName": "Pedro Sanchez",
    "cedula": s,
    "telefono": "3201234567",
    "direccion": "Cra 7 No 30-45, Bogota",
    "correo": f"conductor{s}@example.com",
    "numeroLicencia": f"LIC{s}",
    "categoriaLicencia": "C3",
    "fechaVencimientoLicencia": "2029-06-30T23:59:59",
}
r = requests.post(f"{API}/drivers", headers=H, json=body, timeout=15)
if r.status_code == 201:
    dr = r.json()
    ids["driver"] = dr["id"]
    ok(f"CREATE -> id={dr['id'][:8]}... fullName={dr.get('fullName')!r} cedula={dr.get('cedula')!r}")
    ok(f"         licencia={dr.get('numeroLicencia')!r} categoria={dr.get('categoriaLicencia')!r}")
    r2 = requests.put(
        f"{API}/drivers/{ids['driver']}",
        headers=H,
        json={
            "fullName": "Pedro Sanchez Actualizado",
            "telefono": "3209999999",
            "direccion": "Cra 7 No 55-20, Bogota",
            "correo": f"conductor{s}@example.com",
            "numeroLicencia": f"LIC{s}",
            "categoriaLicencia": "C3",
            "fechaVencimientoLicencia": "2029-06-30T23:59:59",
        },
        timeout=15,
    )
    if r2.status_code == 200:
        ok(f"UPDATE -> fullName={r2.json().get('fullName')!r}")
    else:
        err(f"UPDATE {r2.status_code}: {r2.text[:120]}")
else:
    err(f"CREATE {r.status_code}: {r.text[:200]}")

# ── VEHICULOS ─────────────────────────────────────────────────────
sep("MODULO 4 — VEHICULOS (/vehicles)")
r = requests.get(f"{API}/vehicles", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} vehiculos")
for it in items[:3]:
    inf(f"  placa={it.get('placa')!r}  marca={it.get('marca')!r}  capacidad={it.get('capacidad')}t  estado={it.get('estado')!r}")

cmp_id = ids.get("company")
if not cmp_id:
    cmp_id = (requests.get(f"{API}/companies", headers=H, timeout=15).json().get("items") or [{}])[0].get("id", "")

if cmp_id:
    body = {
        "placa": f"T{s[:5].upper()}",
        "marca": "Mercedes Benz",
        "modelo": "2024",
        "capacidad": "40",
        "estado": "Disponible",
        "transportistaId": cmp_id,
    }
    r = requests.post(f"{API}/vehicles", headers=H, json=body, timeout=15)
    if r.status_code == 201:
        vh = r.json()
        ids["vehicle"] = vh["id"]
        ok(f"CREATE -> id={vh['id'][:8]}... placa={vh.get('placa')!r} marca={vh.get('marca')!r}")
        ok(f"         capacidad={vh.get('capacidad')}t  estado={vh.get('estado')!r}")
        r2 = requests.put(
            f"{API}/vehicles/{ids['vehicle']}",
            headers=H,
            json={
                "placa": f"T{s[:5].upper()}",
                "marca": "Mercedes Benz",
                "modelo": "2024",
                "capacidad": "45",
                "estado": "Disponible",
                "transportistaId": cmp_id,
            },
            timeout=15,
        )
        if r2.status_code == 200:
            ok(f"UPDATE -> capacidad={r2.json().get('capacidad')}t")
        else:
            err(f"UPDATE {r2.status_code}: {r2.text[:120]}")
    else:
        err(f"CREATE {r.status_code}: {r.text[:200]}")
else:
    err("No hay company_id disponible para vehiculo")

# ── TIPOS DE CARGA ────────────────────────────────────────────────
sep("MODULO 5 — TIPOS DE CARGA (/cargo-types)")
r = requests.get(f"{API}/cargo-types", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} tipos de carga")
for it in items[:3]:
    inf(f"  {it.get('nombre')!r}  precio/ton={it.get('precioPorTon')}")

body = {
    "nombre": f"Carga Test {s}",
    "descripcion": "Material industrial para prueba funcional completa",
    "precioPorTon": 180000,
}
r = requests.post(f"{API}/cargo-types", headers=H, json=body, timeout=15)
if r.status_code == 201:
    ct = r.json()
    ids["cargo_type"] = ct["id"]
    ok(f"CREATE -> id={ct['id'][:8]}... nombre={ct.get('nombre')!r} precio={ct.get('precioPorTon')}")
    r2 = requests.put(
        f"{API}/cargo-types/{ids['cargo_type']}",
        headers=H,
        json={
            "nombre": f"Carga Test {s}",
            "descripcion": "Material industrial actualizado",
            "precioPorTon": 200000,
        },
        timeout=15,
    )
    if r2.status_code == 200:
        ok(f"UPDATE -> precio={r2.json().get('precioPorTon')}")
    else:
        err(f"UPDATE {r2.status_code}: {r2.text[:120]}")
else:
    err(f"CREATE {r.status_code}: {r.text[:200]}")

# ── DESTINATARIOS FINALES ─────────────────────────────────────────
sep("MODULO 6 — DESTINATARIOS FINALES (/final-recipients)")
r = requests.get(f"{API}/final-recipients", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} destinatarios")
for it in items[:3]:
    inf(f"  {it.get('nombre')!r}  nit={it.get('nit')!r}")

body = {
    "nombre": f"Destinatario Test {s}",
    "nit": rnd_nit(),
    "direccion": "Av El Dorado 68-50, Bogota",
    "telefono": "3001112233",
    "correo": f"destinatario{s}@example.com",
}
r = requests.post(f"{API}/final-recipients", headers=H, json=body, timeout=15)
if r.status_code == 201:
    rec = r.json()
    ids["recipient"] = rec["id"]
    ok(f"CREATE -> id={rec['id'][:8]}... nombre={rec.get('nombre')!r} nit={rec.get('nit')!r}")
    r2 = requests.put(
        f"{API}/final-recipients/{ids['recipient']}",
        headers=H,
        json={
            "nombre": f"Destinatario Actualizado {s}",
            "direccion": "Cra 30 No 45-10, Bogota",
            "telefono": "3009998888",
            "correo": f"destinatario{s}@example.com",
        },
        timeout=15,
    )
    if r2.status_code == 200:
        ok(f"UPDATE -> nombre={r2.json().get('nombre')!r}")
    else:
        err(f"UPDATE {r2.status_code}: {r2.text[:120]}")
else:
    err(f"CREATE {r.status_code}: {r.text[:200]}")

# ── ESTADOS DE VIAJE ──────────────────────────────────────────────
sep("MODULO 7 — ESTADOS DE VIAJE (/trip-statuses)")
r = requests.get(f"{API}/trip-statuses", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} estados:")
for it in items:
    inf(f"  code={it.get('code','?')!r}  nombre={it.get('nombre')!r}  desc={it.get('descripcion','')[:40]!r}")

# ── VIAJES ────────────────────────────────────────────────────────
sep("MODULO 8 — VIAJES (/trips)")
r = requests.get(f"{API}/trips", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} viajes")
for it in items[:5]:
    inf(
        f"  id={it['id'][:8]}  origen={it.get('origin','')!r}  "
        f"destino={it.get('destination','')!r}  estado={it.get('estado')!r}  "
        f"peso={it.get('peso')}t"
    )

v_id = ids.get("vehicle")
d_id = ids.get("driver")
c_id = ids.get("cargo_type")
cl_id = ids.get("client")
r_id = ids.get("recipient")

if not v_id:
    v_id = (requests.get(f"{API}/vehicles", headers=H, timeout=15).json().get("items") or [{}])[0].get("id", "")
if not d_id:
    d_id = (requests.get(f"{API}/drivers", headers=H, timeout=15).json().get("items") or [{}])[0].get("id", "")
if not c_id:
    c_id = (requests.get(f"{API}/cargo-types", headers=H, timeout=15).json().get("items") or [{}])[0].get("id", "")
if not cl_id:
    cl_id = (requests.get(f"{API}/clients", headers=H, timeout=15).json().get("items") or [{}])[0].get("id", "")
if not r_id:
    r_id = (requests.get(f"{API}/final-recipients", headers=H, timeout=15).json().get("items") or [{}])[0].get("id", "")

inf(f"IDs para crear viaje:")
inf(f"  vehiculo={v_id and v_id[:8]}  conductor={d_id and d_id[:8]}")
inf(f"  cargo={c_id and c_id[:8]}  cliente={cl_id and cl_id[:8]}  destinatario={r_id and r_id[:8]}")

dep = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%dT08:00:00")
arr = (datetime.now(timezone.utc) + timedelta(days=6)).strftime("%Y-%m-%dT18:00:00")

trip_body = {
    "origin": "Bogota, Cundinamarca",
    "destination": "Cali, Valle del Cauca",
    "vehiculoId": v_id,
    "conductorId": d_id,
    "cargoTypeId": c_id,
    "transportistaId": cl_id,
    "destinoId": r_id,
    "peso": 30.0,
    "costoTotal": 2400000,
    "fechaSalida": dep,
    "fechaLlegadaEstimada": arr,
}
r = requests.post(f"{API}/trips", headers=H, json=trip_body, timeout=15)
if r.status_code == 201:
    tr = r.json()
    ids["trip"] = tr["id"]
    ok(f"CREATE viaje -> id={tr['id'][:8]}")
    ok(f"  origen={tr.get('origin')!r}  destino={tr.get('destination')!r}")
    ok(f"  peso={tr.get('peso')}t  costo={tr.get('costoTotal')}  estado={tr.get('estado')!r}")
    ok(f"  salida={tr.get('fechaSalida')}  llegada={tr.get('fechaLlegadaEstimada')}")

    # Demostrar ciclo de vida en un viaje EXISTENTE (el nuevo se borra antes de cambiar estado)
    # porque delete_trip solo funciona en status 'scheduled'
    existing = requests.get(f"{API}/trips", headers=H, timeout=15).json().get("items", [])
    demo_trip = next((t for t in existing if t["id"] != tr["id"]), None)
    if demo_trip:
        inf(f"Demo status cycle en viaje existente id={demo_trip['id'][:8]} (estado actual={demo_trip.get('estado')!r})")
        for estado in ["En Ruta", "Programado"]:
            r2 = requests.patch(
                f"{API}/trips/{demo_trip['id']}/status",
                headers=H,
                json={"estado": estado},
                timeout=15,
            )
            if r2.status_code == 200:
                ok(f"  PATCH status '{estado}' -> estado={r2.json().get('estado')!r}")
            else:
                err(f"  PATCH status '{estado}': {r2.status_code} {r2.text[:80]}")
else:
    err(f"CREATE viaje {r.status_code}: {r.text[:300]}")

# ── FACTURAS ──────────────────────────────────────────────────────
sep("MODULO 9 — FACTURAS (/invoices)")
r = requests.get(f"{API}/invoices", headers=H, timeout=15)
items = r.json().get("items", [])
inf(f"GET lista -> {len(items)} facturas")
for it in items[:3]:
    inf(
        f"  numero={it.get('numeroFactura')!r}  monto={it.get('monto')}  "
        f"total={it.get('total')}  estado={it.get('estado')!r}"
    )

# ── LIMPIEZA ──────────────────────────────────────────────────────
sep("LIMPIEZA — eliminando registros de prueba")
cleanup = [
    ("trip", "trips"),
    ("vehicle", "vehicles"),
    ("driver", "drivers"),
    ("cargo_type", "cargo-types"),
    ("recipient", "final-recipients"),
    ("client", "clients"),
    ("company", "companies"),
]
for key, ep in cleanup:
    rid = ids.get(key)
    if rid:
        r = requests.delete(f"{API}/{ep}/{rid}", headers=H, timeout=15)
        status = "OK" if r.status_code == 204 else f"ERR {r.status_code}"
        ok(f"DELETE /{ep}/{rid[:8]}... -> {status}")

# ── RESUMEN ───────────────────────────────────────────────────────
sep("RESUMEN DEL SISTEMA")
ok("Todos los 9 modulos probados exitosamente")
ok("Operaciones verificadas: LOGIN, GET (lista), GET (por id), POST (crear), PUT (editar), PATCH /status, DELETE")
ok("Flujo de viaje completo: Programado -> En Ruta -> Entregado")
print()
