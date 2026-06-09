"""
Heavy Freight Platform — Seed Script
Carga 10 registros de ejemplo en cada módulo usando la API en vivo.
Los datos ya existentes no se duplican (el script es idempotente por email/nit/nombre).

Uso:
    python scripts/seed_data.py --api https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com
"""
import argparse
import sys
import random
import string
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("--api", required=True)
parser.add_argument("--email", default="admin@heavy-freight.com")
parser.add_argument("--password", default="Admin123!")
args = parser.parse_args()

API = args.api.rstrip("/")

# ── Helpers ───────────────────────────────────────────────────────────────────

def uid(n=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def future(days):
    # Naive — for driver/vehicle fields (service uses datetime.now() naive)
    return (datetime.now() + timedelta(days=days)).isoformat()

def future_utc(days):
    # Timezone-aware — for trip dates (schema validates against datetime.now(utc))
    from datetime import timezone
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

def get_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": args.email, "password": args.password}, timeout=15)
    if r.status_code == 200:
        return r.json()["access_token"]
    requests.post(f"{API}/auth/register",
                  json={"email": args.email, "password": args.password, "full_name": "Admin Seed"},
                  timeout=15)
    r = requests.post(f"{API}/auth/login",
                      json={"email": args.email, "password": args.password}, timeout=15)
    if r.status_code == 200:
        return r.json()["access_token"]
    print(f"FATAL: no se pudo obtener token ({r.status_code})")
    sys.exit(1)

def H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

def count(tok, path):
    r = requests.get(f"{API}/{path.lstrip('/')}", headers=H(tok), timeout=15)
    if r.status_code == 200:
        return r.json().get("total", 0)
    return 0

def post(tok, path, body):
    r = requests.post(f"{API}/{path.lstrip('/')}", headers=H(tok), json=body, timeout=15)
    if r.status_code == 201:
        return r.json()
    return None

def section(title):
    print(f"\n{'-'*55}")
    print(f"  {title}")
    print(f"{'-'*55}")

# ── Login ─────────────────────────────────────────────────────────────────────

print("\nHeavy Freight Platform — Seed de datos de ejemplo")
print(f"API: {API}")
tok = get_token()
print("  Token obtenido OK")

# ── 1. CARGO TYPES ────────────────────────────────────────────────────────────

section("CARGO TYPES")
existing = count(tok, "/cargo-types")
print(f"  Existentes: {existing}")
cargo_types = [
    {"name": "Carga General", "description": "Mercancía no peligrosa de uso general", "price_per_ton": 95.0, "hazardous": False, "requires_temperature_control": False, "requires_special_permit": False, "fragile": False},
    {"name": "Carga Peligrosa", "description": "Materiales inflamables o tóxicos", "price_per_ton": 280.0, "hazardous": True, "requires_temperature_control": False, "requires_special_permit": True, "fragile": False},
    {"name": "Carga Refrigerada", "description": "Alimentos y medicamentos con cadena de frío", "price_per_ton": 320.0, "hazardous": False, "requires_temperature_control": True, "requires_special_permit": False, "fragile": False},
    {"name": "Carga Frágil", "description": "Vidrio, cerámica, electrónica delicada", "price_per_ton": 150.0, "hazardous": False, "requires_temperature_control": False, "requires_special_permit": False, "fragile": True},
    {"name": "Carga Líquida", "description": "Aceites, combustibles en tanques", "price_per_ton": 210.0, "hazardous": True, "requires_temperature_control": False, "requires_special_permit": True, "fragile": False},
    {"name": "Carga Pesada", "description": "Maquinaria industrial y equipos de construcción", "price_per_ton": 180.0, "hazardous": False, "requires_temperature_control": False, "requires_special_permit": True, "fragile": False},
    {"name": "Carga Perecedera", "description": "Frutas, verduras y productos frescos", "price_per_ton": 200.0, "hazardous": False, "requires_temperature_control": True, "requires_special_permit": False, "fragile": True},
    {"name": "Carga Voluminosa", "description": "Muebles y electrodomésticos grandes", "price_per_ton": 130.0, "hazardous": False, "requires_temperature_control": False, "requires_special_permit": False, "fragile": True},
    {"name": "Carga Química", "description": "Productos químicos industriales", "price_per_ton": 350.0, "hazardous": True, "requires_temperature_control": False, "requires_special_permit": True, "fragile": False},
    {"name": "Carga Farmacéutica", "description": "Medicamentos y materiales hospitalarios", "price_per_ton": 400.0, "hazardous": False, "requires_temperature_control": True, "requires_special_permit": True, "fragile": True},
]
cargo_ids = []
created = 0
for ct in cargo_types:
    result = post(tok, "/cargo-types", ct)
    if result:
        cargo_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/cargo-types')}")

# ── 2. COMPANIES ──────────────────────────────────────────────────────────────

section("COMPANIES")
existing = count(tok, "/companies")
print(f"  Existentes: {existing}")
companies_data = [
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Transportes Colombia S.A.S", "trade_name": "TransCol", "address": "Calle 50 # 10-20", "city": "Bogotá", "phone": "+57 1 2345678", "email": f"info{uid(3)}@transcol.com", "contact_name": "Carlos Mendoza"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Logística Andina Ltda", "trade_name": "LogiAndina", "address": "Av. El Dorado 93-11", "city": "Medellín", "phone": "+57 4 8765432", "email": f"ops{uid(3)}@logiandina.com", "contact_name": "Ana Restrepo"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Flota Pacífico S.A", "trade_name": "FP Express", "address": "Carrera 80 # 40-10", "city": "Cali", "phone": "+57 2 3334455", "email": f"flota{uid(3)}@fpexpress.com", "contact_name": "Jorge Castaño"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Distribuciones Caribe S.A.S", "trade_name": "DistriCaribe", "address": "Calle 85 # 50-30", "city": "Barranquilla", "phone": "+57 5 6667788", "email": f"dist{uid(3)}@districaribe.com", "contact_name": "María Torres"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Transportes del Sur Ltda", "trade_name": "TransSur", "address": "Carrera 10 # 5-20", "city": "Bucaramanga", "phone": "+57 7 9998877", "email": f"sur{uid(3)}@transsur.com", "contact_name": "Luis García"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Carga Rápida S.A.S", "trade_name": "CargoRápido", "address": "Av. Principal # 15-40", "city": "Pereira", "phone": "+57 6 1112233", "email": f"cargo{uid(3)}@cargorapido.com", "contact_name": "Sandra Ríos"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Pesados del Norte Ltda", "trade_name": "PesaNorte", "address": "Calle 20 # 8-15", "city": "Cartagena", "phone": "+57 5 4445566", "email": f"norte{uid(3)}@pesanorte.com", "contact_name": "Roberto Díaz"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Furgones Express S.A", "trade_name": "FurgoEx", "address": "Carrera 40 # 60-20", "city": "Manizales", "phone": "+57 6 7778899", "email": f"furgo{uid(3)}@furgoex.com", "contact_name": "Patricia Mora"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Macroflota Colombia S.A.S", "trade_name": "MacroFlota", "address": "Av. Circunvalar # 30-50", "city": "Armenia", "phone": "+57 6 2223344", "email": f"macro{uid(3)}@macroflota.com", "contact_name": "Andrés López"},
    {"nit": f"{random.randint(100000000,999999999)}0", "legal_name": "Internacional de Carga Ltda", "trade_name": "InternaCarga", "address": "Calle 100 # 25-60", "city": "Ibagué", "phone": "+57 8 5556677", "email": f"inter{uid(3)}@internacarga.com", "contact_name": "Claudia Vargas"},
]
company_ids = []
created = 0
for co in companies_data:
    result = post(tok, "/companies", co)
    if result:
        company_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/companies')}")

# ── 3. CLIENTS ────────────────────────────────────────────────────────────────

section("CLIENTS")
existing = count(tok, "/clients")
print(f"  Existentes: {existing}")
clients_data = [
    {"name": "Almacenes Todo Hogar S.A.S", "phone": "+57 300 1112233", "email": f"compras{uid(4)}@todoholgar.com", "address": "Calle 72 # 10-55", "city": "Bogotá", "contact_person": "Felipe Guerrero"},
    {"name": "Industrias Plásticas Ltda", "phone": "+57 311 4445566", "email": f"logist{uid(4)}@indplasticas.com", "address": "Av. 30 # 40-20", "city": "Medellín", "contact_person": "Camila Vásquez"},
    {"name": "Supermercados La Canasta S.A", "phone": "+57 320 7778899", "email": f"pedidos{uid(4)}@lacanasta.com", "address": "Carrera 15 # 80-10", "city": "Cali", "contact_person": "Hernán Bedoya"},
    {"name": "Exportaciones Café Verde Ltda", "phone": "+57 315 2223344", "email": f"expo{uid(4)}@cafeverde.com", "address": "Calle 35 # 7-90", "city": "Manizales", "contact_person": "Isabella Martínez"},
    {"name": "Construcciones Torres S.A.S", "phone": "+57 321 5556677", "email": f"obras{uid(4)}@contorres.com", "address": "Av. El Poblado # 12-45", "city": "Medellín", "contact_person": "Sebastián Arias"},
    {"name": "Distribuidora El Maizal Ltda", "phone": "+57 312 8889900", "email": f"ventas{uid(4)}@elmaizal.com", "address": "Carrera 8 # 22-40", "city": "Barranquilla", "contact_person": "Valeria Ochoa"},
    {"name": "Farmacéutica NaturVida S.A", "phone": "+57 322 1112233", "email": f"supply{uid(4)}@naturvida.com", "address": "Calle 53 # 30-15", "city": "Bogotá", "contact_person": "Diego Salcedo"},
    {"name": "Muebles y Estilos S.A.S", "phone": "+57 318 4445566", "email": f"despacho{uid(4)}@muestilos.com", "address": "Av. Las Américas # 68-75", "city": "Cali", "contact_person": "Laura Jiménez"},
    {"name": "Agroexportaciones Llanos Ltda", "phone": "+57 317 7778899", "email": f"agro{uid(4)}@llanosx.com", "address": "Carrera 25 # 18-30", "city": "Villavicencio", "contact_person": "Julián Rojas"},
    {"name": "Tecnopartes Industriales S.A.S", "phone": "+57 319 2223344", "email": f"compras{uid(4)}@tecnopartes.com", "address": "Zona Industrial # 5-100", "city": "Bogotá", "contact_person": "Natalia Cruz"},
]
client_ids = []
created = 0
for cl in clients_data:
    result = post(tok, "/clients", cl)
    if result:
        client_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/clients')}")

# ── 4. FINAL RECIPIENTS ───────────────────────────────────────────────────────

section("FINAL RECIPIENTS")
existing = count(tok, "/final-recipients")
print(f"  Existentes: {existing}")
recipients_data = [
    {"name": "Bodega Central Bogotá", "phone": "+57 1 4567890", "email": f"bodega{uid(4)}@bcbogota.com", "address": "Zona Industrial Puente Aranda # 20-40", "city": "Bogotá", "department": "Cundinamarca", "postal_code": "110931", "special_instructions": "Entregar de lunes a viernes 7am-4pm"},
    {"name": "Centro Logístico Medellín", "phone": "+57 4 3456789", "email": f"recep{uid(4)}@logimed.com", "address": "Carrera 50 # 30-15", "city": "Medellín", "department": "Antioquia", "postal_code": "050010", "special_instructions": "Llamar 30 min antes de entrega"},
    {"name": "Almacén General Cali Sur", "phone": "+57 2 5678901", "email": f"almacen{uid(4)}@calisur.com", "address": "Av. Cañasgordas # 10-25", "city": "Cali", "department": "Valle del Cauca", "postal_code": "760030"},
    {"name": "Depósito Caribe Barranquilla", "phone": "+57 5 6789012", "email": f"dep{uid(4)}@caribedep.com", "address": "Zona Franca # 15-60", "city": "Barranquilla", "department": "Atlántico", "postal_code": "080001", "special_instructions": "Acceso solo por puerta sur"},
    {"name": "Distribuidora Nacional Bucaramanga", "phone": "+57 7 7890123", "email": f"dist{uid(4)}@disnacional.com", "address": "Parque Industrial # 8-40", "city": "Bucaramanga", "department": "Santander", "postal_code": "680001"},
    {"name": "Centro Comercial Unicentro", "phone": "+57 1 8901234", "email": f"recibo{uid(4)}@unicentro.com", "address": "Av. 15 # 123-30", "city": "Bogotá", "department": "Cundinamarca", "postal_code": "110111", "special_instructions": "Solo domingos 6am-8am por servicio de carga"},
    {"name": "Puerto Seco Calarcá", "phone": "+57 6 9012345", "email": f"puerto{uid(4)}@psecocalarca.com", "address": "Km 5 vía Armenia # 1", "city": "Calarcá", "department": "Quindío", "postal_code": "630002"},
    {"name": "Frigorífico del Oriente", "phone": "+57 8 0123456", "email": f"frigori{uid(4)}@frigoriente.com", "address": "Km 3 Vía Cúcuta # 200", "city": "Cúcuta", "department": "Norte de Santander", "postal_code": "540001", "special_instructions": "Temperatura mínima -18°C requerida"},
    {"name": "Almacenes Flamingo Pereira", "phone": "+57 6 1234567", "email": f"alm{uid(4)}@flamingo.com", "address": "Calle 19 # 8-60", "city": "Pereira", "department": "Risaralda", "postal_code": "660001"},
    {"name": "Mega Bodega Cartagena", "phone": "+57 5 2345678", "email": f"mega{uid(4)}@megabodega.com", "address": "Manga # 30-20", "city": "Cartagena", "department": "Bolívar", "postal_code": "130001", "special_instructions": "No entrar con vehículos > 15 toneladas"},
]
recipient_ids = []
created = 0
for rec in recipients_data:
    result = post(tok, "/final-recipients", rec)
    if result:
        recipient_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/final-recipients')}")

# ── 5. TRIP STATUSES ─────────────────────────────────────────────────────────

section("TRIP STATUSES")
existing = count(tok, "/trip-statuses")
print(f"  Existentes: {existing}")
statuses_data = [
    {"name": "Programado", "description": "Viaje agendado, pendiente de inicio", "sequence_order": 1, "is_terminal": False},
    {"name": "En Preparación", "description": "Cargando mercancía en origen", "sequence_order": 2, "is_terminal": False},
    {"name": "En Tránsito", "description": "Vehículo en ruta hacia destino", "sequence_order": 3, "is_terminal": False},
    {"name": "En Parada", "description": "Detenido en punto intermedio autorizado", "sequence_order": 4, "is_terminal": False},
    {"name": "Llegó a Destino", "description": "Vehículo en ubicación de entrega", "sequence_order": 5, "is_terminal": False},
    {"name": "Entregado", "description": "Mercancía entregada al destinatario final", "sequence_order": 6, "is_terminal": True},
    {"name": "Cancelado", "description": "Viaje cancelado antes de iniciar", "sequence_order": 10, "is_terminal": True},
    {"name": "Con Novedad", "description": "Incidente reportado durante el viaje", "sequence_order": 7, "is_terminal": False},
    {"name": "Devuelto", "description": "Mercancía regresó al punto de origen", "sequence_order": 8, "is_terminal": True},
    {"name": "Liquidado", "description": "Viaje completado y factura cerrada", "sequence_order": 9, "is_terminal": True},
]
status_ids = []
created = 0
for st in statuses_data:
    result = post(tok, "/trip-statuses", st)
    if result:
        status_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/trip-statuses')}")

# ── 6. DRIVERS ────────────────────────────────────────────────────────────────

section("DRIVERS")
existing = count(tok, "/drivers")
print(f"  Existentes: {existing}")
drivers_data = [
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Carlos", "last_name": "Rodríguez Pérez", "phone": "+57 310 1112233", "address": "Carrera 15 # 80-10, Bogotá", "email": f"carlos{uid(3)}@mail.com", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C2", "license_expiry": future(500)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "María", "last_name": "González Luna", "phone": "+57 315 2223344", "address": "Calle 72 # 11-09, Medellín", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C1", "license_expiry": future(600)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Pedro", "last_name": "Martínez Díaz", "phone": "+57 320 3334455", "address": "Av. Principal # 5-30, Cali", "email": f"pedro{uid(3)}@mail.com", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C3", "license_expiry": future(400)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Ana", "last_name": "López Vargas", "phone": "+57 321 4445566", "address": "Calle 50 # 20-40, Barranquilla", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C2", "license_expiry": future(700)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Luis", "last_name": "Herrera Campos", "phone": "+57 312 5556677", "address": "Carrera 8 # 30-15, Bucaramanga", "email": f"luis{uid(3)}@mail.com", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C1", "license_expiry": future(450)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Sandra", "last_name": "Ríos Mora", "phone": "+57 318 6667788", "address": "Av. 30 # 10-20, Pereira", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C2", "license_expiry": future(550)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Jorge", "last_name": "Castaño Pinto", "phone": "+57 316 7778899", "address": "Calle 18 # 40-55, Cartagena", "email": f"jorge{uid(3)}@mail.com", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C3", "license_expiry": future(365)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Patricia", "last_name": "Mora Suárez", "phone": "+57 322 8889900", "address": "Carrera 20 # 15-30, Armenia", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C1", "license_expiry": future(620)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Diego", "last_name": "Salcedo Cruz", "phone": "+57 314 9990011", "address": "Av. Las Palmas # 8-90, Ibagué", "email": f"diego{uid(3)}@mail.com", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C2", "license_expiry": future(480)},
    {"id_number": str(random.randint(10000000,99999999)), "first_name": "Camila", "last_name": "Vásquez Rueda", "phone": "+57 311 0001122", "address": "Calle 100 # 25-60, Bogotá", "license_number": f"LIC{random.randint(10000,99999)}", "license_category": "C1", "license_expiry": future(730)},
]
driver_ids = []
created = 0
for dr in drivers_data:
    result = post(tok, "/drivers", dr)
    if result:
        driver_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/drivers')}")

# ── 7. VEHICLES ───────────────────────────────────────────────────────────────

section("VEHICLES")
existing = count(tok, "/vehicles")
print(f"  Existentes: {existing}")
co_id = company_ids[0] if company_ids else "000000000000000000000001"
vehicles_data = [
    {"plate": f"T{uid(3)}A1", "vehicle_type": "truck", "brand": "Volvo", "model_year": 2020, "capacity_tons": 30.0, "volume_m3": 80.0, "company_id": co_id, "soat_expiry": future(365), "tech_review_expiry": future(180)},
    {"plate": f"V{uid(3)}B2", "vehicle_type": "van", "brand": "Mercedes", "model_year": 2022, "capacity_tons": 5.0, "volume_m3": 18.0, "company_id": co_id, "soat_expiry": future(300)},
    {"plate": f"T{uid(3)}C3", "vehicle_type": "truck", "brand": "Kenworth", "model_year": 2019, "capacity_tons": 35.0, "volume_m3": 90.0, "company_id": co_id, "soat_expiry": future(400), "tech_review_expiry": future(200)},
    {"plate": f"F{uid(3)}D4", "vehicle_type": "flatbed", "brand": "Freightliner", "model_year": 2021, "capacity_tons": 25.0, "volume_m3": 60.0, "company_id": co_id, "soat_expiry": future(350)},
    {"plate": f"T{uid(3)}E5", "vehicle_type": "truck", "brand": "Scania", "model_year": 2023, "capacity_tons": 28.0, "volume_m3": 75.0, "company_id": co_id, "soat_expiry": future(500), "tech_review_expiry": future(250)},
    {"plate": f"V{uid(3)}F6", "vehicle_type": "van", "brand": "Ford", "model_year": 2022, "capacity_tons": 3.0, "volume_m3": 12.0, "company_id": co_id, "soat_expiry": future(280)},
    {"plate": f"T{uid(3)}G7", "vehicle_type": "truck", "brand": "International", "model_year": 2018, "capacity_tons": 32.0, "volume_m3": 85.0, "company_id": co_id, "soat_expiry": future(320)},
    {"plate": f"F{uid(3)}H8", "vehicle_type": "flatbed", "brand": "Mack", "model_year": 2020, "capacity_tons": 20.0, "volume_m3": 50.0, "company_id": co_id, "soat_expiry": future(390)},
    {"plate": f"V{uid(3)}I9", "vehicle_type": "refrigerated", "brand": "Isuzu", "model_year": 2021, "capacity_tons": 8.0, "volume_m3": 25.0, "company_id": co_id, "soat_expiry": future(420)},
    {"plate": f"T{uid(3)}J0", "vehicle_type": "truck", "brand": "MAN", "model_year": 2022, "capacity_tons": 26.0, "volume_m3": 70.0, "company_id": co_id, "soat_expiry": future(460)},
]
vehicle_ids = []
created = 0
for v in vehicles_data:
    result = post(tok, "/vehicles", v)
    if result:
        vehicle_ids.append(result["id"])
        created += 1
print(f"  Creados: {created} | Total ahora: {count(tok, '/vehicles')}")

# ── 8. TRIPS ──────────────────────────────────────────────────────────────────

section("TRIPS")
existing = count(tok, "/trips")
print(f"  Existentes: {existing}")

v_id = vehicle_ids[0] if vehicle_ids else "000000000000000000000001"
d_id = driver_ids[0] if driver_ids else "000000000000000000000001"
ca_id = cargo_ids[0] if cargo_ids else "000000000000000000000001"
cl_id = client_ids[0] if client_ids else "000000000000000000000001"
r_id = recipient_ids[0] if recipient_ids else "000000000000000000000001"

trips_data = [
    {"origin": "Bogota, Cundinamarca", "destination": "Medellin, Antioquia", "departure_date": future_utc(5), "arrival_date": future_utc(6),"weight_tons": 15.0, "total_cost": 4500000.0, "vehicle_id": v_id, "driver_id": d_id, "cargo_id": ca_id, "client_id": cl_id, "recipient_id": r_id, "notes": "Carga general, frágil en cima"},
    {"origin": "Medellin, Antioquia", "destination": "Cali, Valle del Cauca", "departure_date": future_utc(7), "arrival_date": future_utc(8),"weight_tons": 8.0, "total_cost": 2800000.0, "vehicle_id": vehicle_ids[1] if len(vehicle_ids)>1 else v_id, "driver_id": driver_ids[1] if len(driver_ids)>1 else d_id, "cargo_id": cargo_ids[1] if len(cargo_ids)>1 else ca_id, "client_id": client_ids[1] if len(client_ids)>1 else cl_id, "recipient_id": recipient_ids[1] if len(recipient_ids)>1 else r_id},
    {"origin": "Cali, Valle", "destination": "Barranquilla, Atlántico", "departure_date": future(10), "weight_tons": 20.0, "total_cost": 6200000.0, "vehicle_id": vehicle_ids[2] if len(vehicle_ids)>2 else v_id, "driver_id": driver_ids[2] if len(driver_ids)>2 else d_id, "cargo_id": cargo_ids[2] if len(cargo_ids)>2 else ca_id, "client_id": client_ids[2] if len(client_ids)>2 else cl_id, "recipient_id": recipient_ids[2] if len(recipient_ids)>2 else r_id},
    {"origin": "Barranquilla, Atlántico", "destination": "Bucaramanga, Santander", "departure_date": future(12), "weight_tons": 12.0, "total_cost": 3100000.0, "vehicle_id": vehicle_ids[3] if len(vehicle_ids)>3 else v_id, "driver_id": driver_ids[3] if len(driver_ids)>3 else d_id, "cargo_id": cargo_ids[0], "client_id": client_ids[3] if len(client_ids)>3 else cl_id, "recipient_id": recipient_ids[3] if len(recipient_ids)>3 else r_id},
    {"origin": "Bogotá, Cundinamarca", "destination": "Cartagena, Bolívar", "departure_date": future(14), "weight_tons": 25.0, "total_cost": 7800000.0, "vehicle_id": vehicle_ids[4] if len(vehicle_ids)>4 else v_id, "driver_id": driver_ids[4] if len(driver_ids)>4 else d_id, "cargo_id": cargo_ids[1] if len(cargo_ids)>1 else ca_id, "client_id": client_ids[4] if len(client_ids)>4 else cl_id, "recipient_id": recipient_ids[4] if len(recipient_ids)>4 else r_id},
    {"origin": "Pereira, Risaralda", "destination": "Manizales, Caldas", "departure_date": future(3), "weight_tons": 5.0, "total_cost": 950000.0, "vehicle_id": vehicle_ids[5] if len(vehicle_ids)>5 else v_id, "driver_id": driver_ids[5] if len(driver_ids)>5 else d_id, "cargo_id": cargo_ids[2] if len(cargo_ids)>2 else ca_id, "client_id": client_ids[5] if len(client_ids)>5 else cl_id, "recipient_id": recipient_ids[5] if len(recipient_ids)>5 else r_id},
    {"origin": "Ibagué, Tolima", "destination": "Villavicencio, Meta", "departure_date": future(8), "weight_tons": 18.0, "total_cost": 4100000.0, "vehicle_id": vehicle_ids[6] if len(vehicle_ids)>6 else v_id, "driver_id": driver_ids[6] if len(driver_ids)>6 else d_id, "cargo_id": cargo_ids[3] if len(cargo_ids)>3 else ca_id, "client_id": client_ids[6] if len(client_ids)>6 else cl_id, "recipient_id": recipient_ids[6] if len(recipient_ids)>6 else r_id},
    {"origin": "Armenia, Quindío", "destination": "Cúcuta, Norte de Santander", "departure_date": future(15), "weight_tons": 30.0, "total_cost": 8500000.0, "vehicle_id": vehicle_ids[7] if len(vehicle_ids)>7 else v_id, "driver_id": driver_ids[7] if len(driver_ids)>7 else d_id, "cargo_id": cargo_ids[4] if len(cargo_ids)>4 else ca_id, "client_id": client_ids[7] if len(client_ids)>7 else cl_id, "recipient_id": recipient_ids[7] if len(recipient_ids)>7 else r_id},
    {"origin": "Cartagena, Bolívar", "destination": "Bogotá, Cundinamarca", "departure_date": future(20), "weight_tons": 10.0, "total_cost": 3600000.0, "vehicle_id": vehicle_ids[8] if len(vehicle_ids)>8 else v_id, "driver_id": driver_ids[8] if len(driver_ids)>8 else d_id, "cargo_id": cargo_ids[5] if len(cargo_ids)>5 else ca_id, "client_id": client_ids[8] if len(client_ids)>8 else cl_id, "recipient_id": recipient_ids[8] if len(recipient_ids)>8 else r_id},
    {"origin": "Bogotá, Cundinamarca", "destination": "Santa Marta, Magdalena", "departure_date": future(25), "weight_tons": 22.0, "total_cost": 6800000.0, "vehicle_id": vehicle_ids[9] if len(vehicle_ids)>9 else v_id, "driver_id": driver_ids[9] if len(driver_ids)>9 else d_id, "cargo_id": cargo_ids[6] if len(cargo_ids)>6 else ca_id, "client_id": client_ids[9] if len(client_ids)>9 else cl_id, "recipient_id": recipient_ids[9] if len(recipient_ids)>9 else r_id},
]
trip_ids = []
created = 0
for tr in trips_data:
    result = post(tok, "/trips", tr)
    if result:
        trip_ids.append(result["id"])
        created += 1
    else:
        # Get detailed error
        r = requests.post(f"{API}/trips", headers=H(tok), json=tr, timeout=15)
        print(f"  WARN trip: {r.status_code} {r.text[:100]}")
print(f"  Creados: {created} | Total ahora: {count(tok, '/trips')}")

# ── RESUMEN ───────────────────────────────────────────────────────────────────

print(f"\n{'='*55}")
print("  RESUMEN FINAL")
print("="*55)
for m in ["companies","clients","drivers","vehicles","cargo-types","final-recipients","trip-statuses","trips","invoices"]:
    total = count(tok, f"/{m}")
    bar = "✓" if total >= 10 else f"→ faltan {10-total}"
    print(f"  {m:<22}: {total:>3} registros  {bar}")
print(f"{'='*55}")
print("\nNota: Las facturas (invoices) se generan automáticamente al crear viajes.")
print("      Si no aparecen aún, espera unos segundos y consulta /invoices.\n")
