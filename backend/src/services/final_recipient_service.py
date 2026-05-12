"""
Final Recipients service - business logic layer for final recipients.
"""
from datetime import datetime, timezone
from src.repositories.final_recipient_repository import FinalRecipientRepository
from src.domain.final_recipient import (
    validate_recipient_data,
    sanitize_recipient_name,
    recipient_to_dict,
    recipient_from_dict
)


class FinalRecipientError(Exception):
    """Base exception for final recipient service errors."""
    pass


class FinalRecipientNotFoundError(FinalRecipientError):
    """Raised when final recipient is not found."""
    pass


class FinalRecipientValidationError(FinalRecipientError):
    """Raised when final recipient data fails validation."""
    pass


class FinalRecipientAlreadyExistsError(FinalRecipientError):
    """Raised when attempting to create final recipient that already exists."""
    pass


# Aliases for backward compatibility
RecipientNotFoundError = FinalRecipientNotFoundError
ValidationError = FinalRecipientValidationError
AlreadyExistsError = FinalRecipientAlreadyExistsError


class FinalRecipientService:
    """
    Service layer for final recipient business logic.
    Handles CRUD operations and validation.
    """
    
    def __init__(self, repository: FinalRecipientRepository):
        """
        Initialize FinalRecipientService.
        
        Args:
            repository: FinalRecipientRepository instance
        """
        self.repository = repository
    
    def create_recipient(self, data: dict) -> dict:
        """
        Create a new final recipient.
        
        Args:
            data: Recipient data (name, address, city, contact_name, phone, email)
            
        Returns:
            Created recipient document with _id
            
        Raises:
            FinalRecipientValidationError: If data validation fails
            FinalRecipientAlreadyExistsError: If email already exists
        """
        # Validate data
        if not validate_recipient_data(data):
            raise FinalRecipientValidationError("Invalid recipient data")
        
        # Check if recipient with same email already exists
        existing = self.repository.find_one({
            "email": data.get("email", "").lower(),
            "is_active": True
        })
        if existing:
            raise FinalRecipientAlreadyExistsError(
                f"Recipient with email '{data.get('email')}' already exists"
            )
        
        # Prepare recipient record
        recipient = {
            "name": sanitize_recipient_name(data["name"]),
            "address": data.get("address", "").strip(),
            "city": data.get("city", "").strip(),
            "contact_name": data.get("contact_name", "").strip(),
            "phone": data.get("phone", "").strip(),
            "email": data.get("email", "").lower().strip(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        return self.repository.insert_one(recipient)
    
    def get_recipient(self, recipient_id: str) -> dict:
        """
        Get a specific recipient by ID.
        
        Args:
            recipient_id: Recipient ID as string
            
        Returns:
            Recipient document
            
        Raises:
            FinalRecipientNotFoundError: If recipient not found
        """
        recipient = self.repository.find_by_id(recipient_id)
        if not recipient or not recipient.get("is_active"):
            raise FinalRecipientNotFoundError(f"Recipient {recipient_id} not found")
        return recipient
    
    def list_recipients(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """
        List all active recipients with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return (capped at 100)
            
        Returns:
            List of active recipient documents
        """
        # Cap limit at 100
        limit = min(limit, 100)
        
        return self.repository.find_many(
            {"is_active": True},
            skip=skip,
            limit=limit
        )
    
    def search_recipients_by_name(self, name: str, limit: int = 10) -> list[dict]:
        """
        Search recipients by name (case-insensitive, partial match).
        
        Args:
            name: Recipient name or partial name
            limit: Maximum results
            
        Returns:
            List of matching recipient documents
        """
        if not name or len(name.strip()) < 2:
            raise FinalRecipientValidationError("Search name must be at least 2 characters")
        
        return self.repository.find_by_name(name, limit=limit)
    
    def update_recipient(self, recipient_id: str, data: dict) -> dict:
        """
        Update an existing recipient.
        
        Args:
            recipient_id: Recipient ID as string
            data: Data to update (name, address, city, contact_name, phone, email)
            
        Returns:
            Updated recipient document
            
        Raises:
            FinalRecipientNotFoundError: If recipient not found
            FinalRecipientValidationError: If data validation fails
            FinalRecipientAlreadyExistsError: If email already exists for another recipient
        """
        # Verify recipient exists and is active
        existing = self.repository.find_by_id(recipient_id)
        if not existing or not existing.get("is_active"):
            raise FinalRecipientNotFoundError(f"Recipient {recipient_id} not found")
        
        # If email is being changed, verify uniqueness
        if "email" in data:
            new_email = data["email"].lower().strip()
            if new_email != existing.get("email"):
                email_exists = self.repository.find_one({
                    "email": new_email,
                    "_id": {"$ne": existing["_id"]},
                    "is_active": True
                })
                if email_exists:
                    raise FinalRecipientAlreadyExistsError(
                        f"Email '{new_email}' already exists for another recipient"
                    )
        
        # Validate update data
        update_fields = {k: v for k, v in data.items() 
                        if k in ["name", "address", "city", "contact_name", "phone", "email"]}
        
        if update_fields:
            # Create full record for validation
            full_data = {**existing, **update_fields}
            if not validate_recipient_data(full_data):
                raise FinalRecipientValidationError("Invalid recipient data")
        
        # Prepare update with normalized fields
        update_data = {}
        if "name" in data:
            update_data["name"] = sanitize_recipient_name(data["name"])
        if "address" in data:
            update_data["address"] = data["address"].strip()
        if "city" in data:
            update_data["city"] = data["city"].strip()
        if "contact_name" in data:
            update_data["contact_name"] = data["contact_name"].strip()
        if "phone" in data:
            update_data["phone"] = data["phone"].strip()
        if "email" in data:
            update_data["email"] = data["email"].lower().strip()
        
        if update_data:
            self.repository.update(recipient_id, update_data)
        
        # Return updated document
        return self.repository.find_by_id(recipient_id)
    
    def delete_recipient(self, recipient_id: str) -> bool:
        """
        Soft delete a recipient (mark as inactive).
        
        Args:
            recipient_id: Recipient ID as string
            
        Returns:
            True if successful
            
        Raises:
            FinalRecipientNotFoundError: If recipient not found
        """
        existing = self.repository.find_by_id(recipient_id)
        if not existing or not existing.get("is_active"):
            raise FinalRecipientNotFoundError(f"Recipient {recipient_id} not found")
        
        return self.repository.soft_delete(recipient_id)
    
    def count_active(self) -> int:
        """
        Count active recipients.
        
        Returns:
            Number of active recipients
        """
        return self.repository.collection.count_documents({"is_active": True})
