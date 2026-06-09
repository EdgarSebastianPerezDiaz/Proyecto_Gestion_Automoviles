"""
Create invoices directly in MongoDB for existing trips (no POST endpoint exists yet).
Uses the same logic as InvoiceService.create_invoice().
"""
import sys
from datetime import datetime, timezone
from bson import ObjectId

try:
    from pymongo import MongoClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo", "-q"])
    from pymongo import MongoClient

MONGO_URI = "mongodb+srv://edgarperez02_db_user:MFv1waDmj4Vl1UcR@clustertransport.jxlpljp.mongodb.net/?appName=ClusterTransport"
DB_NAME   = "heavy_freight"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DB_NAME]

trips_col    = db["trips"]
invoices_col = db["invoices"]

trips = list(trips_col.find({"is_active": {"$ne": False}}))
print(f"Trips found: {len(trips)}")

existing_trip_ids = {str(inv.get("trip_id")) for inv in invoices_col.find({}, {"trip_id": 1})}
print(f"Trips already invoiced: {len(existing_trip_ids)}")

TAX_RATE = 0.19
created = 0

for i, trip in enumerate(trips):
    trip_id_str = str(trip["_id"])
    if trip_id_str in existing_trip_ids:
        print(f"  [SKIP] Trip {i+1}: already has invoice")
        continue

    base_amount = float(trip.get("total_cost", 0))
    tax_amount  = round(base_amount * TAX_RATE, 2)
    total       = round(base_amount + tax_amount, 2)

    # Generate invoice number
    last = invoices_col.find_one({}, sort=[("invoice_number", -1)])
    next_num = (int(last["invoice_number"].split("-")[-1]) + 1) if last and last.get("invoice_number") else 1
    inv_number = f"INV-{next_num:06d}"

    invoice = {
        "invoice_number": inv_number,
        "trip_id": str(trip["_id"]),
        "client_id": str(trip.get("client_id", "")),
        "amount": base_amount,
        "tax_amount": tax_amount,
        "total_amount": total,
        "currency": "COP",
        "status": "issued",
        "issued_at": datetime.now(timezone.utc),
        "paid_at": None,
        "pdf_url": None,
        "notes": trip.get("notes"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    invoices_col.insert_one(invoice)
    created += 1
    print(f"  [OK ] Invoice {inv_number}: trip {trip.get('origin','?')} -> {trip.get('destination','?')} | ${total:,.0f} COP")

total_inv = invoices_col.count_documents({})
print(f"\nCreated: {created} invoices | Total invoices in DB: {total_inv}")
client.close()
