"""Add missing trip statuses that Angular expects but don't exist in the DB."""
import requests

API = "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com"
tok = requests.post(f"{API}/auth/login",
    json={"email": "admin@heavy-freight.com", "password": "Admin123!"}, timeout=15
).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

statuses = [
    {"name": "En Ruta",    "description": "Viaje en curso hacia el destino", "sequence_order": 3, "is_terminal": False},
    {"name": "Completado", "description": "Viaje completado exitosamente",   "sequence_order": 6, "is_terminal": True},
]

for s in statuses:
    r = requests.post(f"{API}/trip-statuses", headers=H, json=s, timeout=15)
    if r.status_code == 201:
        d = r.json()
        print(f"  [OK] code={d.get('code')} nombre={d.get('nombre')}")
    elif r.status_code == 409:
        print(f"  [SKIP] '{s['name']}' ya existe")
    else:
        print(f"  [ERR] {r.status_code}: {r.text[:100]}")

# Verify all codes
all_statuses = requests.get(f"{API}/trip-statuses", headers=H, timeout=15).json()
print("\nCodigos existentes:")
for s in all_statuses.get("items", []):
    print(f"  {s.get('code','?'):25} -> {s.get('nombre','?')}")
