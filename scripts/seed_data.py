"""
Poblar el sistema con datos simulados realistas para que el dashboard se vea completo.
Crea empresas, clientes, conductores, vehiculos, tipos de carga, destinatarios y viajes
con distintos estados.
"""
import sys, io, requests, random, time
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com"

# ── helpers ───────────────────────────────────────────────────────────────────
def sep(t):  print(f"\n{'='*60}\n  {t}\n{'='*60}")
def ok(m):   print(f"  [OK]   {m}")
def err(m):  print(f"  [ERR]  {m}")
def inf(m):  print(f"         {m}")

def post(path, body):
    r = requests.post(f"{API}{path}", headers=H, json=body, timeout=20)
    return r

def patch_status(trip_id, code):
    r = requests.patch(f"{API}/trips/{trip_id}/status", headers=H,
                       json={"status_code": code}, timeout=20)
    return r

# ── LOGIN ─────────────────────────────────────────────────────────────────────
sep("LOGIN")
r = requests.post(f"{API}/auth/login",
                  json={"email": "admin@heavy-freight.com", "password": "Admin123!"},
                  timeout=15)
if r.status_code != 200:
    err(f"Login fallido {r.status_code}: {r.text}")
    sys.exit(1)
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
ok("Login exitoso")

# ── 1. EMPRESAS ───────────────────────────────────────────────────────────────
sep("EMPRESAS")
empresas_data = [
    {"nombre": "Logistica Andina S.A.S",        "nit": "800.123.456-7", "direccion": "Cra 15 #93-47, Bogota",          "telefono": "6013456789", "correo": "contacto@logisticaandina.com"},
    {"nombre": "Transportes del Pacifico Ltda",  "nit": "900.234.567-8", "direccion": "Av 3N #12-45, Cali",             "telefono": "6024567890", "correo": "info@transppacifico.com"},
    {"nombre": "Flota del Caribe S.A",           "nit": "890.345.678-9", "direccion": "Calle 72 #50-21, Barranquilla",  "telefono": "6056789012", "correo": "operaciones@flotacaribe.com"},
    {"nombre": "Alianza Transportadora Ltda",    "nit": "860.456.789-0", "direccion": "Cra 49 #54-23, Medellin",        "telefono": "6044321098", "correo": "admin@alianzatrans.com"},
    {"nombre": "Carga Segura Colombia S.A.S",    "nit": "901.567.890-1", "direccion": "Av Americas #24-56, Bogota",     "telefono": "6013219876", "correo": "ventas@cargasegura.com"},
]
company_ids = []
for e in empresas_data:
    r = post("/companies", e)
    if r.status_code == 201:
        cid = r.json()["id"]
        company_ids.append(cid)
        ok(f"Empresa '{e['nombre']}' -> id={cid[:8]}")
    elif r.status_code == 409:
        inf(f"Empresa '{e['nombre']}' ya existe (409) — buscando id...")
        existing = requests.get(f"{API}/companies", headers=H, timeout=15).json().get("items", [])
        for ex in existing:
            if ex.get("nit") == e["nit"] or ex.get("nombre") == e["nombre"]:
                company_ids.append(ex["id"])
                inf(f"  id={ex['id'][:8]} (reutilizado)")
                break
    else:
        err(f"Empresa '{e['nombre']}': {r.status_code} {r.text[:80]}")

# ── 2. CLIENTES (transportistas) ───────────────────────────────────────────────
sep("CLIENTES")
clientes_data = [
    {"nombre": "Almacenes Exito S.A",      "nit": "860.007.538-1", "direccion": "Calle 80 #70-60, Bogota",       "telefono": "6013001234", "correo": "logistica@exito.com",          "tipoDocumento": "NIT"},
    {"nombre": "Postobon S.A.S",           "nit": "860.002.525-5", "direccion": "Av El Dorado #90-10, Bogota",   "telefono": "6012991000", "correo": "compras@postobon.com",          "tipoDocumento": "NIT"},
    {"nombre": "Bavaria S.A",              "nit": "860.034.313-7", "direccion": "Cra 53A #127-35, Bogota",       "telefono": "6016600000", "correo": "supply@bavaria.com.co",         "tipoDocumento": "NIT"},
    {"nombre": "Grupo Familia S.A.S",      "nit": "890.300.513-2", "direccion": "Cra 43A #7-50, Medellin",      "telefono": "6044441100", "correo": "compras@grupofamilia.com",       "tipoDocumento": "NIT"},
    {"nombre": "Corona S.A",               "nit": "860.007.382-3", "direccion": "Autopista Norte #131-80, Bogota","telefono": "6017456789", "correo": "logistica@corona.com.co",       "tipoDocumento": "NIT"},
    {"nombre": "Colombina S.A",            "nit": "890.324.568-9", "direccion": "Calle 10 #4-47, La Paila",     "telefono": "6023561234", "correo": "ventas@colombina.com",           "tipoDocumento": "NIT"},
]
client_ids = []
for c in clientes_data:
    r = post("/clients", c)
    if r.status_code == 201:
        cid = r.json()["id"]
        client_ids.append(cid)
        ok(f"Cliente '{c['nombre']}' -> id={cid[:8]}")
    elif r.status_code == 409:
        inf(f"Cliente '{c['nombre']}' ya existe — reutilizando")
        existing = requests.get(f"{API}/clients", headers=H, timeout=15).json().get("items", [])
        for ex in existing:
            if ex.get("nombre") == c["nombre"]:
                client_ids.append(ex["id"])
                inf(f"  id={ex['id'][:8]} (reutilizado)")
                break
    else:
        err(f"Cliente '{c['nombre']}': {r.status_code} {r.text[:80]}")

# ── 3. CONDUCTORES ────────────────────────────────────────────────────────────
sep("CONDUCTORES")
conductores_data = [
    {"fullName": "Juan Carlos Perez Rodriguez",  "cedula": "12345678", "telefono": "3001234001", "direccion": "Calle 45 #23-12, Bogota",    "correo": "jcperez@gmail.com",    "numeroLicencia": "LIC001COL", "categoriaLicencia": "C2", "fechaVencimientoLicencia": "2027-12-31T23:59:59"},
    {"fullName": "Andres Felipe Torres Mesa",    "cedula": "23456789", "telefono": "3112345002", "direccion": "Cra 8 #12-45, Cali",          "correo": "aftorres@gmail.com",   "numeroLicencia": "LIC002COL", "categoriaLicencia": "C3", "fechaVencimientoLicencia": "2028-06-30T23:59:59"},
    {"fullName": "Ricardo Antonio Gomez Vargas", "cedula": "34567890", "telefono": "3201234003", "direccion": "Av 30 #45-67, Medellin",      "correo": "ragomez@hotmail.com",  "numeroLicencia": "LIC003COL", "categoriaLicencia": "C2", "fechaVencimientoLicencia": "2027-03-15T23:59:59"},
    {"fullName": "Luis Alberto Martinez Soto",   "cedula": "45678901", "telefono": "3004567004", "direccion": "Calle 72 #15-30, Barranquilla","correo": "lamartinez@gmail.com", "numeroLicencia": "LIC004COL", "categoriaLicencia": "C1", "fechaVencimientoLicencia": "2029-01-20T23:59:59"},
    {"fullName": "Carlos Arturo Diaz Hernandez", "cedula": "56789012", "telefono": "3153456005", "direccion": "Cra 27 #48-32, Bucaramanga",  "correo": "cadiaz@gmail.com",     "numeroLicencia": "LIC005COL", "categoriaLicencia": "C3", "fechaVencimientoLicencia": "2028-09-10T23:59:59"},
    {"fullName": "Miguel Angel Ruiz Castro",     "cedula": "67890123", "telefono": "3024567006", "direccion": "Calle 10 #5-22, Pereira",     "correo": "maruiz@gmail.com",     "numeroLicencia": "LIC006COL", "categoriaLicencia": "C2", "fechaVencimientoLicencia": "2027-07-25T23:59:59"},
    {"fullName": "Eduardo Jose Ramirez Pinto",   "cedula": "78901234", "telefono": "3175678007", "direccion": "Av 3 #23-45, Cucuta",         "correo": "ejramirez@gmail.com",  "numeroLicencia": "LIC007COL", "categoriaLicencia": "C1", "fechaVencimientoLicencia": "2028-11-30T23:59:59"},
    {"fullName": "Fernando Andres Lopez Mora",   "cedula": "89012345", "telefono": "3056789008", "direccion": "Cra 15 #8-30, Manizales",     "correo": "falopez@gmail.com",    "numeroLicencia": "LIC008COL", "categoriaLicencia": "C3", "fechaVencimientoLicencia": "2029-04-15T23:59:59"},
]
driver_ids = []
for d in conductores_data:
    r = post("/drivers", d)
    if r.status_code == 201:
        did = r.json()["id"]
        driver_ids.append(did)
        ok(f"Conductor '{d['fullName']}' cedula={d['cedula']} -> id={did[:8]}")
    elif r.status_code == 409:
        inf(f"Conductor cedula={d['cedula']} ya existe — reutilizando")
        existing = requests.get(f"{API}/drivers", headers=H, timeout=15).json().get("items", [])
        for ex in existing:
            if ex.get("cedula") == d["cedula"]:
                driver_ids.append(ex["id"])
                inf(f"  id={ex['id'][:8]} (reutilizado)")
                break
    else:
        err(f"Conductor '{d['fullName']}': {r.status_code} {r.text[:100]}")

# ── 4. VEHÍCULOS ──────────────────────────────────────────────────────────────
sep("VEHICULOS")
vehicle_ids = []
if not company_ids:
    err("No hay empresas — omitiendo vehiculos")
else:
    vehiculos_data = [
        {"placa": "VHF001", "marca": "Kenworth",       "modelo": 2022, "capacidad": 35.0, "transportistaId": company_ids[0 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF002", "marca": "Freightliner",   "modelo": 2021, "capacidad": 30.0, "transportistaId": company_ids[0 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF003", "marca": "Volvo",          "modelo": 2023, "capacidad": 40.0, "transportistaId": company_ids[1 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF004", "marca": "Mack",           "modelo": 2020, "capacidad": 28.0, "transportistaId": company_ids[1 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF005", "marca": "International",  "modelo": 2022, "capacidad": 32.0, "transportistaId": company_ids[2 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF006", "marca": "Mercedes-Benz",  "modelo": 2021, "capacidad": 25.0, "transportistaId": company_ids[2 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF007", "marca": "Scania",         "modelo": 2023, "capacidad": 38.0, "transportistaId": company_ids[3 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF008", "marca": "Kenworth",       "modelo": 2019, "capacidad": 22.0, "transportistaId": company_ids[3 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF009", "marca": "Volvo",          "modelo": 2024, "capacidad": 45.0, "transportistaId": company_ids[4 % len(company_ids)], "estado": "Disponible"},
        {"placa": "VHF010", "marca": "Freightliner",   "modelo": 2022, "capacidad": 33.0, "transportistaId": company_ids[4 % len(company_ids)], "estado": "Disponible"},
    ]
    for v in vehiculos_data:
        r = post("/vehicles", v)
        if r.status_code == 201:
            vid = r.json()["id"]
            vehicle_ids.append(vid)
            ok(f"Vehiculo {v['placa']} {v['marca']} {v['modelo']} -> id={vid[:8]}")
        elif r.status_code == 409:
            inf(f"Vehiculo '{v['placa']}' ya existe — reutilizando")
            existing = requests.get(f"{API}/vehicles", headers=H, timeout=15).json().get("items", [])
            for ex in existing:
                if ex.get("placa") == v["placa"]:
                    vehicle_ids.append(ex["id"])
                    inf(f"  id={ex['id'][:8]} (reutilizado)")
                    break
        else:
            err(f"Vehiculo '{v['placa']}': {r.status_code} {r.text[:100]}")

# ── 5. TIPOS DE CARGA ─────────────────────────────────────────────────────────
sep("TIPOS DE CARGA")
cargos_data = [
    {"nombre": "Alimentos Perecederos",    "descripcion": "Frutas, verduras y productos refrigerados",   "precioPorTon": 250000.0},
    {"nombre": "Bebidas y Liquidos",       "descripcion": "Agua, jugos, gaseosas y licores",             "precioPorTon": 180000.0},
    {"nombre": "Materiales Construccion",  "descripcion": "Cemento, arena, bloques y varillas",          "precioPorTon": 85000.0},
    {"nombre": "Productos Industriales",   "descripcion": "Maquinaria, repuestos y equipos",             "precioPorTon": 320000.0},
    {"nombre": "Textiles y Confeccion",    "descripcion": "Ropa, telas y calzado",                       "precioPorTon": 420000.0},
    {"nombre": "Electrodomesticos",        "descripcion": "Neveras, lavadoras y televisores",            "precioPorTon": 380000.0},
    {"nombre": "Papel y Carton",           "descripcion": "Resmas, cajas y empaques",                    "precioPorTon": 140000.0},
    {"nombre": "Productos Quimicos",       "descripcion": "Fertilizantes y agroquimicos (no peligrosos)","precioPorTon": 195000.0},
]
cargo_ids = []
for c in cargos_data:
    r = post("/cargo-types", c)
    if r.status_code == 201:
        cid = r.json()["id"]
        cargo_ids.append(cid)
        ok(f"Tipo carga '{c['nombre']}' -> id={cid[:8]}")
    elif r.status_code == 409:
        inf(f"Tipo carga '{c['nombre']}' ya existe — reutilizando")
        existing = requests.get(f"{API}/cargo-types", headers=H, timeout=15).json().get("items", [])
        for ex in existing:
            if ex.get("nombre") == c["nombre"]:
                cargo_ids.append(ex["id"])
                inf(f"  id={ex['id'][:8]} (reutilizado)")
                break
    else:
        err(f"Tipo carga '{c['nombre']}': {r.status_code} {r.text[:80]}")

# ── 6. DESTINATARIOS FINALES ──────────────────────────────────────────────────
sep("DESTINATARIOS FINALES")
destinatarios_data = [
    {"nombre": "Bodega Logistica Norte",          "nit": "900.111.222-3", "direccion": "Zona Industrial Calle 80, Bogota",   "telefono": "6013334455", "correo": "bodega.norte@logistica.com"},
    {"nombre": "Centro Distribucion Medellin",    "nit": "811.222.333-4", "direccion": "Autopista Sur Km 5, Medellin",       "telefono": "6044556677", "correo": "cd.medellin@distribucion.com"},
    {"nombre": "Puerto Logistico Barranquilla",   "nit": "890.333.444-5", "direccion": "Cra 46 #74-50, Barranquilla",        "telefono": "6055667788", "correo": "puerto@logbarranquilla.com"},
    {"nombre": "Almacen Exito Cali Norte",        "nit": "860.007.539-6", "direccion": "Av 6N #25N-103, Cali",              "telefono": "6024445566", "correo": "logistica.calinorte@exito.com"},
    {"nombre": "Planta Bavaria Tocancipa",        "nit": "860.034.314-8", "direccion": "Via Briceno Km 7, Tocancipa",       "telefono": "6018887766", "correo": "planta.tocancipa@bavaria.com"},
    {"nombre": "Planta Postobon Bogota",          "nit": "860.002.526-9", "direccion": "Av Esperanza #65-50, Bogota",       "telefono": "6012990011", "correo": "planta.bogota@postobon.com"},
    {"nombre": "Bodega Colombina Cali",           "nit": "890.324.569-0", "direccion": "Calle 25 #28-40, Cali",            "telefono": "6023456789", "correo": "bodega.cali@colombina.com"},
    {"nombre": "CEDIS Corona Bogota",             "nit": "860.007.383-4", "direccion": "Cra 97 #24-55, Bogota",            "telefono": "6017654321", "correo": "cedis@corona.com.co"},
]
recipient_ids = []
for d in destinatarios_data:
    r = post("/final-recipients", d)
    if r.status_code == 201:
        rid = r.json()["id"]
        recipient_ids.append(rid)
        ok(f"Destinatario '{d['nombre']}' -> id={rid[:8]}")
    elif r.status_code == 409:
        inf(f"Destinatario '{d['nombre']}' ya existe — reutilizando")
        existing = requests.get(f"{API}/final-recipients", headers=H, timeout=15).json().get("items", [])
        for ex in existing:
            if ex.get("nombre") == d["nombre"]:
                recipient_ids.append(ex["id"])
                inf(f"  id={ex['id'][:8]} (reutilizado)")
                break
    else:
        err(f"Destinatario '{d['nombre']}': {r.status_code} {r.text[:80]}")

# ── 7. VIAJES ─────────────────────────────────────────────────────────────────
sep("VIAJES")

if not (vehicle_ids and driver_ids and cargo_ids and client_ids and recipient_ids):
    err("Faltan IDs para crear viajes — revisar errores anteriores")
else:
    now = datetime.now(timezone.utc)

    # (origen_txt, destino_txt, offset_salida_dias, duracion_dias, peso_t, status_code)
    # Todos se crean con fecha futura (validador rechaza pasado), luego se parchea el estado
    viajes_config = [
        ("Bogota, Cundinamarca",    "Medellin, Antioquia",      1,  3,  22.5,  "en_ruta"),
        ("Cali, Valle del Cauca",   "Bogota, Cundinamarca",     1,  3,  18.0,  "en_ruta"),
        ("Barranquilla, Atlantico", "Bogota, Cundinamarca",     2,  4,  30.0,  "en_ruta"),
        ("Bogota, Cundinamarca",    "Cali, Valle del Cauca",    2,  4,  25.0,  "entregado"),
        ("Medellin, Antioquia",     "Barranquilla, Atlantico",  3,  5,  15.5,  "entregado"),
        ("Bogota, Cundinamarca",    "Cartagena, Bolivar",       3,  6,  28.0,  "entregado"),
        ("Cucuta, Norte Santander", "Bogota, Cundinamarca",     4,  6,  20.0,  "entregado"),
        ("Bogota, Cundinamarca",    "Bucaramanga, Santander",   5,  7,  19.0,  "programado"),
        ("Medellin, Antioquia",     "Cali, Valle del Cauca",    6,  8,  35.0,  "programado"),
        ("Barranquilla, Atlantico", "Medellin, Antioquia",      7, 10,  22.0,  "programado"),
        ("Bogota, Cundinamarca",    "Pereira, Risaralda",       8, 10,  12.0,  "programado"),
        ("Cali, Valle del Cauca",   "Pasto, Narino",            9, 11,  16.5,  "programado"),
    ]

    created_trips = []
    for i, (origen, destino, d_sal, duracion, peso, status) in enumerate(viajes_config):
        v_id  = vehicle_ids[i % len(vehicle_ids)]
        dr_id = driver_ids[i % len(driver_ids)]
        c_id  = cargo_ids[i % len(cargo_ids)]
        cl_id = client_ids[i % len(client_ids)]
        r_id  = recipient_ids[i % len(recipient_ids)]

        sal  = (now + timedelta(days=d_sal)).replace(hour=8,  minute=0, second=0, microsecond=0)
        ll   = (now + timedelta(days=d_sal + duracion)).replace(hour=18, minute=0, second=0, microsecond=0)
        costo = round(peso * 200000, 2)

        body = {
            "origin":               origen,   # required text field in TripCreate
            "destination":          destino,  # required text field in TripCreate
            "vehiculoId":           v_id,
            "conductorId":          dr_id,
            "cargoTypeId":          c_id,
            "transportistaId":      cl_id,
            "destinoId":            r_id,
            "peso":                 peso,
            "costoTotal":           costo,
            "fechaSalida":          sal.isoformat(),
            "fechaLlegadaEstimada": ll.isoformat(),
        }

        r = post("/trips", body)
        if r.status_code == 201:
            trip = r.json()
            tid = trip["id"]
            created_trips.append(tid)
            estado_inicial = trip.get("estado", "?")
            ok(f"Viaje {i+1:02d}: {origen[:22]:22s} -> {destino[:22]:22s}  {peso}t  estado='{estado_inicial}'")

            if status != "programado":
                time.sleep(0.3)
                rp = patch_status(tid, status)
                if rp.status_code == 200:
                    estado_final = rp.json().get("estado", "?")
                    ok(f"         PATCH '{status}' -> estado='{estado_final}'")
                else:
                    err(f"         PATCH: {rp.status_code} {rp.text[:80]}")
        else:
            err(f"Viaje {i+1:02d}: {r.status_code} {r.text[:120]}")

# ── RESUMEN ───────────────────────────────────────────────────────────────────
sep("RESUMEN FINAL")
inf(f"Empresas:         {len(company_ids)}")
inf(f"Clientes:         {len(client_ids)}")
inf(f"Conductores:      {len(driver_ids)}")
inf(f"Vehiculos:        {len(vehicle_ids)}")
inf(f"Tipos de carga:   {len(cargo_ids)}")
inf(f"Destinatarios:    {len(recipient_ids)}")
inf(f"Viajes:           {len(created_trips) if 'created_trips' in dir() else 0}")
inf("")
ok("Datos cargados. El dashboard ahora muestra actividad real.")
