"""
Cargo Types service - business logic layer for cargo types.
"""
from datetime import datetime, timezone
from decimal import Decimal
from src.repositories.cargo_type_repository import CargoTypeRepository
from src.domain.cargo_type import (
    validate_cargo_type_data,
    sanitize_cargo_name,
    cargo_type_to_dict,
    cargo_type_from_dict
)


class CargoTypeError(Exception):
    """Base exception for cargo type service errors."""
    pass


class CargoTypeNotFoundError(CargoTypeError):
    """Raised when cargo type is not found."""
    pass


class CargoTypeValidationError(CargoTypeError):
    """Raised when cargo type data fails validation."""
    pass


class CargoTypeAlreadyExistsError(CargoTypeError):
    """Raised when attempting to create cargo type that already exists."""
    pass


# Aliases for backward compatibility
ValidationError = CargoTypeValidationError
AlreadyExistsError = CargoTypeAlreadyExistsError


class CargoTypeService:
    """
    Service layer for cargo type business logic.
    Handles CRUD operations and validation.
    """
    
    def __init__(self, repository: CargoTypeRepository):
        """
        Initialize CargoTypeService.
        
        Args:
            repository: CargoTypeRepository instance
        """
        self.repository = repository
    
    def create_cargo_type(self, data: dict) -> dict:
        """
        Create a new cargo type.
        
        Args:
            data: Cargo type data (name, description, price_per_ton, requires_special_permit)
            
        Returns:
            Created cargo type document with _id
            
        Raises:
            CargoTypeValidationError: If data validation fails
            CargoTypeAlreadyExistsError: If name already exists
        """
        # Validate data
        is_valid, error_msg = validate_cargo_type_data(data)
        if not is_valid:
            raise CargoTypeValidationError(error_msg)
        
        # Check if cargo type with same name already exists
        existing = self.repository.find_by_name(data.get("name", ""))
        if existing:
            raise CargoTypeAlreadyExistsError(
                f"Cargo type with name '{data.get('name')}' already exists"
            )
        
        # Prepare cargo type record
        price = data.get("price_per_ton", 0)
        if isinstance(price, (int, float)):
            price = float(price)
        
        cargo_type = {
            "name": sanitize_cargo_name(data["name"]),
            "description": data.get("description", "").strip(),
            "price_per_ton": price,
            "requires_special_permit": bool(data.get("requires_special_permit", False)),
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        return self.repository.insert_one(cargo_type)
    
    def get_cargo_type(self, cargo_id: str) -> dict:
        """
        Get a specific cargo type by ID.
        
        Args:
            cargo_id: Cargo type ID as string
            
        Returns:
            Cargo type document
            
        Raises:
            CargoTypeNotFoundError: If cargo type not found
        """
        cargo_type = self.repository.find_by_id(cargo_id)
        if not cargo_type or not cargo_type.get("is_active"):
            raise CargoTypeNotFoundError(f"Cargo type {cargo_id} not found")
        return cargo_type
    
    def list_active_cargo_types(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """
        List all active cargo types with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of active cargo type documents
        """
        return self.repository.find_active(limit=limit, skip=skip)
    
    def search_cargo_type_by_name(self, name: str) -> dict:
        """
        Search for cargo type by exact name match (case-insensitive).
        
        Args:
            name: Cargo type name
            
        Returns:
            Cargo type document
            
        Raises:
            CargoTypeNotFoundError: If cargo type not found
            ValidationError: If name is invalid
        """
        if not name or len(name.strip()) < 2:
            raise CargoTypeValidationError("Cargo name must be at least 2 characters")
        
        cargo_type = self.repository.find_by_name(name)
        if not cargo_type:
            raise CargoTypeNotFoundError(f"Cargo type '{name}' not found")
        
        return cargo_type
    
    def update_cargo_type(self, cargo_id: str, data: dict) -> dict:
        """
        Update an existing cargo type.
        
        Args:
            cargo_id: Cargo type ID as string
            data: Data to update (name, description, price_per_ton, requires_special_permit)
            
        Returns:
            Updated cargo type document
            
        Raises:
            CargoTypeNotFoundError: If cargo type not found
            CargoTypeValidationError: If data validation fails
            CargoTypeAlreadyExistsError: If name already exists for another cargo type
        """
        # Verify cargo type exists and is active
        existing = self.repository.find_by_id(cargo_id)
        if not existing or not existing.get("is_active"):
            raise CargoTypeNotFoundError(f"Cargo type {cargo_id} not found")
        
        # If name is being changed, verify uniqueness
        if "name" in data:
            new_name = data["name"].strip()
            if new_name.lower() != existing.get("name", "").lower():
                name_exists = self.repository.find_one({
                    "name": {"$regex": f"^{new_name}$", "$options": "i"},
                    "_id": {"$ne": existing["_id"]},
                    "is_active": True
                })
                if name_exists:
                    raise CargoTypeAlreadyExistsError(
                        f"Cargo type name '{new_name}' already exists"
                    )
        
        # Validate update data
        update_fields = {k: v for k, v in data.items() 
                        if k in ["name", "description", "price_per_ton", "requires_special_permit"]}
        
        if update_fields:
            # Create full record for validation
            full_data = {**existing, **update_fields}
            is_valid, error_msg = validate_cargo_type_data(full_data)
            if not is_valid:
                raise CargoTypeValidationError(error_msg)
        
        # Prepare update with normalized fields
        update_data = {}
        if "name" in data:
            update_data["name"] = sanitize_cargo_name(data["name"])
        if "description" in data:
            update_data["description"] = data["description"].strip()
        if "price_per_ton" in data:
            price = data["price_per_ton"]
            if isinstance(price, (int, float)):
                update_data["price_per_ton"] = float(price)
        if "requires_special_permit" in data:
            update_data["requires_special_permit"] = bool(data["requires_special_permit"])
        
        if update_data:
            self.repository.update(cargo_id, update_data)
        
        # Return updated document
        return self.repository.find_by_id(cargo_id)
    
    def delete_cargo_type(self, cargo_id: str) -> bool:
        """
        Soft delete a cargo type (mark as inactive).
        
        Args:
            cargo_id: Cargo type ID as string
            
        Returns:
            True if successful
            
        Raises:
            CargoTypeNotFoundError: If cargo type not found
        """
        existing = self.repository.find_by_id(cargo_id)
        if not existing or not existing.get("is_active"):
            raise CargoTypeNotFoundError(f"Cargo type {cargo_id} not found")
        
        return self.repository.soft_delete(cargo_id)
    
    def count_active(self) -> int:
        """
        Count active cargo types.
        
        Returns:
            Number of active cargo types
        """
        return self.repository.collection.count_documents({"is_active": True})
    
    def get_pricing_by_name(self, cargo_name: str) -> float:
        """
        Get price per ton for a cargo type by name.
        
        Args:
            cargo_name: Cargo type name
            
        Returns:
            Price per ton as float
            
        Raises:
            CargoTypeNotFoundError: If cargo type not found
        """
        cargo_type = self.search_cargo_type_by_name(cargo_name)
        return float(cargo_type.get("price_per_ton", 0))
