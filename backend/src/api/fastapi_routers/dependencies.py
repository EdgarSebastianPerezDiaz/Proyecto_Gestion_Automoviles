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
_VEHICLE_ESTADO_TO_STATUS = {"Disponible": "available", "En Viaje": "on_trip", "Inactivo": "inactive"}


def from_frontend(collection: str, body: dict) -> dict:
    """Translate Angular form Spanish field names to English schema field names.
    Filters out None and empty-string values. Callers must add required defaults for CREATE."""
    r = {k: v for k, v in body.items() if v is not None and v != ""}

    if collection == "companies":
        if "nombre" in r:    r["legal_name"] = r.pop("nombre")
        if "direccion" in r: r["address"]    = r.pop("direccion")
        if "telefono" in r:  r["phone"]      = r.pop("telefono")
        if "correo" in r:    r["email"]      = r.pop("correo")
        r.pop("id", None)

    elif collection == "clients":
        if "nombre" in r:    r["name"]    = r.pop("nombre")
        if "direccion" in r: r["address"] = r.pop("direccion")
        if "telefono" in r:  r["phone"]   = r.pop("telefono")
        if "correo" in r:    r["email"]   = r.pop("correo")
        for k in ("nit", "tipoDocumento", "id"):
            r.pop(k, None)

    elif collection == "drivers":
        if "fullName" in r:
            parts = r.pop("fullName").split(None, 1)
            r["first_name"] = parts[0] if parts else "Sin"
            r["last_name"]  = parts[1] if len(parts) > 1 else "Apellido"
        if "cedula" in r:            r["id_number"]        = r.pop("cedula")
        if "telefono" in r:          r["phone"]             = r.pop("telefono")
        if "correo" in r:            r["email"]             = r.pop("correo")
        if "direccion" in r:         r["address"]           = r.pop("direccion")
        if "numeroLicencia" in r:    r["license_number"]    = r.pop("numeroLicencia")
        if "categoriaLicencia" in r: r["license_category"]  = r.pop("categoriaLicencia")
        if "fechaVencimientoLicencia" in r:
            r["license_expiry"] = r.pop("fechaVencimientoLicencia")
        for k in ("id", "transportistaId"):
            r.pop(k, None)

    elif collection == "vehicles":
        if "placa" in r:           r["plate"]         = r.pop("placa")
        if "marca" in r:           r["brand"]          = r.pop("marca")
        if "modelo" in r:
            try:    r["model_year"] = int(r.pop("modelo"))
            except (ValueError, TypeError): r.pop("modelo", None)
        if "capacidad" in r:       r["capacity_tons"]  = float(r.pop("capacidad"))
        if "transportistaId" in r: r["company_id"]     = r.pop("transportistaId")
        if "estado" in r:
            r["status"] = _VEHICLE_ESTADO_TO_STATUS.get(r.pop("estado"), "available")
        for k in ("conductorId", "id"):
            r.pop(k, None)

    elif collection == "cargo_types":
        if "nombre" in r:       r["name"]          = r.pop("nombre")
        if "descripcion" in r:  r["description"]   = r.pop("descripcion")
        if "precioPorTon" in r: r["price_per_ton"] = float(r.pop("precioPorTon"))
        for k in ("pesoReferencia", "id"):
            r.pop(k, None)

    elif collection == "final_recipients":
        if "nombre" in r:    r["name"]    = r.pop("nombre")
        if "direccion" in r: r["address"] = r.pop("direccion")
        if "telefono" in r:  r["phone"]   = r.pop("telefono")
        if "correo" in r:    r["email"]   = r.pop("correo")
        r.pop("id", None)
        # nit is NOT in FinalRecipientCreate schema — router extracts and stores it separately

    elif collection == "trips":
        if "vehiculoId" in r:           r["vehicle_id"]     = r.pop("vehiculoId")
        if "conductorId" in r:          r["driver_id"]      = r.pop("conductorId")
        if "cargoTypeId" in r:          r["cargo_id"]       = r.pop("cargoTypeId")
        if "transportistaId" in r:      r["client_id"]      = r.pop("transportistaId")
        if "destinoId" in r:            r["recipient_id"]   = r.pop("destinoId")
        if "origenId" in r:             r.pop("origenId")   # origin text sent separately
        if "peso" in r:                 r["weight_tons"]    = float(r.pop("peso"))
        if "costoTotal" in r:           r["total_cost"]     = float(r.pop("costoTotal"))
        if "fechaSalida" in r:          r["departure_date"] = r.pop("fechaSalida")
        if "fechaLlegadaEstimada" in r: r["arrival_date"]   = r.pop("fechaLlegadaEstimada")
        for k in ("id", "estado", "fechaLlegadaReal", "documentos", "precioPorTon",
                  "origenNombre", "destinoNombre", "cargoTypeNombre", "vehiculoPlaca",
                  "vehiculoCapacidad", "conductorNombre", "transportistaNombre"):
            r.pop(k, None)

    return r


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
        r["nombre"] = r.get("name") or ""
        r["nit"] = r.get("nit") or ""
        r["direccion"] = r.get("address") or ""
        r["telefono"] = r.get("phone") or ""
        r["correo"] = r.get("email") or ""

    elif collection == "drivers":
        r["fullName"] = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        r["cedula"] = r.get("id_number") or ""
        r["telefono"] = r.get("phone") or ""
        r["correo"] = r.get("email") or ""
        r["direccion"] = r.get("address") or ""
        r["numeroLicencia"] = r.get("license_number") or ""
        r["categoriaLicencia"] = r.get("license_category") or ""
        r["fechaVencimientoLicencia"] = str(r.get("license_expiry") or "")

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
        r["nombre"] = r.get("name") or ""
        r["nit"] = r.get("nit") or ""
        r["direccion"] = r.get("address") or ""
        r["telefono"] = r.get("phone") or ""
        r["correo"] = r.get("email") or ""

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
