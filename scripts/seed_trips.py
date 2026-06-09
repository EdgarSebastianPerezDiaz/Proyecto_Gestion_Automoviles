"""Quick seed: create 10 trips using existing data from the live API."""
import sys, requests
from datetime import datetime, timedelta, timezone

API = "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com"

def future_utc(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

tok = requests.post(f"{API}/auth/login",
    json={"email": "admin@heavy-freight.com", "password": "Admin123!"}, timeout=15
).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

vehicles   = requests.get(f"{API}/vehicles",         headers=H, timeout=15).json()["items"]
drivers    = requests.get(f"{API}/drivers",          headers=H, timeout=15).json()["items"]
cargos     = requests.get(f"{API}/cargo-types",      headers=H, timeout=15).json()["items"]
clients    = requests.get(f"{API}/clients",          headers=H, timeout=15).json()["items"]
recipients = requests.get(f"{API}/final-recipients", headers=H, timeout=15).json()["items"]

print(f"Available: vehicles={len(vehicles)} drivers={len(drivers)} cargos={len(cargos)} clients={len(clients)} recipients={len(recipients)}")

v  = lambda i: vehicles[i % len(vehicles)]["id"]
dr = lambda i: drivers[i % len(drivers)]["id"]
ca = lambda i: cargos[i % len(cargos)]["id"]
cl = lambda i: clients[i % len(clients)]["id"]
rc = lambda i: recipients[i % len(recipients)]["id"]

ROUTES = [
    ("Bogota", "Medellin", 5, 6, 15.0, 4500000.0),
    ("Medellin", "Cali", 7, 8, 8.0, 2800000.0),
    ("Cali", "Barranquilla", 10, 11, 20.0, 6200000.0),
    ("Barranquilla", "Bucaramanga", 12, 13, 12.0, 3100000.0),
    ("Bogota", "Cartagena", 14, 15, 25.0, 7800000.0),
    ("Pereira", "Manizales", 3, 4, 5.0, 950000.0),
    ("Ibague", "Villavicencio", 8, 9, 18.0, 4100000.0),
    ("Armenia", "Cucuta", 15, 16, 30.0, 8500000.0),
    ("Cartagena", "Bogota", 20, 21, 10.0, 3600000.0),
    ("Bogota", "Santa Marta", 25, 26, 22.0, 6800000.0),
]

created = 0
for i, (orig, dest, dep, arr, kg, cost) in enumerate(ROUTES):
    body = {
        "origin": orig,
        "destination": dest,
        "departure_date": future_utc(dep),
        "arrival_date": future_utc(arr),
        "weight_tons": kg,
        "total_cost": cost,
        "vehicle_id": v(i),
        "driver_id": dr(i),
        "cargo_id": ca(i),
        "client_id": cl(i),
        "recipient_id": rc(i),
    }
    r = requests.post(f"{API}/trips", headers=H, json=body, timeout=15)
    if r.status_code == 201:
        created += 1
        print(f"  [OK ] Trip {i+1}: {orig} -> {dest}")
    else:
        print(f"  [ERR] Trip {i+1}: {r.status_code} | {r.text[:180]}")

trips_total = requests.get(f"{API}/trips",    headers=H, timeout=15).json().get("total", 0)
inv_total   = requests.get(f"{API}/invoices", headers=H, timeout=15).json().get("total", 0)

print(f"\nTrips creados ahora: {created}/10")
print(f"Total trips en DB  : {trips_total}")
print(f"Total invoices     : {inv_total}")
