"""Shared FastAPI dependencies: database access and JWT authentication."""
import os
from typing import Optional, Any
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
from jose import jwt, JWTError

_db_connection = None
_security = HTTPBearer()


def set_db(db) -> None:
    global _db_connection
    _db_connection = db


def get_db():
    if _db_connection is None:
        raise HTTPException(status_code=503, detail="Database connection not initialized")
    return _db_connection


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> dict:
    secret = os.getenv("JWT_SECRET_KEY")
    algo = os.getenv("JWT_ALGORITHM", "HS256")
    if not secret:
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY not configured")
    try:
        payload = jwt.decode(credentials.credentials, secret, algorithms=[algo])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def serialize_doc(doc: Optional[dict]) -> Optional[dict]:
    """Convert MongoDB document to JSON-serializable dict (ObjectId → str)."""
    if doc is None:
        return None
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result["id"] = str(v)
        elif hasattr(v, "__str__") and type(v).__name__ == "ObjectId":
            result[k] = str(v)
        elif isinstance(v, dict):
            result[k] = serialize_doc(v)
        elif isinstance(v, list):
            result[k] = [serialize_doc(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


_VEHICLE_STATUS = {"available": "Disponible", "on_trip": "En Viaje", "inactive": "Inactivo"}


def to_frontend(collection: str, doc: Optional[dict]) -> Optional[dict]:
    """Serialize a MongoDB doc and add Spanish field aliases expected by the Angular frontend."""
    r = serialize_doc(doc)
    if r is None:
        return None

    if collection == "companies":
        r["nombre"] = r.get("legal_name") or r.get("trade_name", "")
        r["direccion"] = r.get("address", "")
        r["telefono"] = r.get("phone", "")
        r["correo"] = r.get("email", "")

    elif collection == "clients":
        r["nombre"] = r.get("name", "")
        r["direccion"] = r.get("address", "")
        r["telefono"] = r.get("phone", "")
        r["correo"] = r.get("email", "")

    elif collection == "drivers":
        r["fullName"] = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
        r["cedula"] = r.get("id_number", "")
        r["telefono"] = r.get("phone", "")
        r["correo"] = r.get("email", "")
        r["direccion"] = r.get("address", "")
        r["numeroLicencia"] = r.get("license_number", "")
        r["categoriaLicencia"] = r.get("license_category", "")
        r["fechaVencimientoLicencia"] = str(r.get("license_expiry", ""))

    elif collection == "cargo_types":
        r["nombre"] = r.get("name", "")
        r["descripcion"] = r.get("description", "")
        r["precioPorTon"] = r.get("price_per_ton", 0)

    elif collection == "vehicles":
        r["placa"] = r.get("plate", "")
        r["marca"] = r.get("brand", "")
        r["modelo"] = str(r.get("model_year", ""))
        r["capacidad"] = r.get("capacity_tons", 0)
        r["transportistaId"] = r.get("company_id", "")
        r["estado"] = _VEHICLE_STATUS.get(r.get("status", ""), r.get("status", "Disponible"))

    elif collection == "final_recipients":
        r["nombre"] = r.get("name", "")
        r["direccion"] = r.get("address", "")
        r["telefono"] = r.get("phone", "")
        r["correo"] = r.get("email", "")

    elif collection == "trips":
        r["fechaSalida"] = r.get("departure_date")
        r["fechaLlegadaEstimada"] = r.get("arrival_date")
        r["fechaLlegadaReal"] = r.get("actual_arrival_date")
        r["peso"] = r.get("weight_tons", 0)
        r["costoTotal"] = r.get("total_cost", 0)
        r["vehiculoId"] = r.get("vehicle_id", "")
        r["conductorId"] = r.get("driver_id", "")
        r["cargoTypeId"] = r.get("cargo_id", "")
        r["documentos"] = r.get("documents", {})
        r["estado"] = r.get("status") or "Programado"

    elif collection == "trip_statuses":
        r["nombre"] = r.get("name", "")
        r["descripcion"] = r.get("description", "")

    elif collection == "invoices":
        r["numeroFactura"] = r.get("invoice_number", "")
        r["monto"] = r.get("amount", 0)
        r["impuesto"] = r.get("tax_amount", 0)
        r["total"] = r.get("total_amount", 0)
        r["estado"] = r.get("status", "")

    return r
