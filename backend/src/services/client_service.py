"""
Client service - business logic layer for client operations.
"""
from typing import Optional
from datetime import datetime, timezone

from src.repositories.client_repository import ClientRepository, RepositoryError
from src.domain.client import sanitize_nit, validate_nit_format, client_from_dict
from src.infrastructure.sanitizer import sanitize_string


class ClientError(Exception):
    """Base exception for client service errors."""
    pass


class ClientAlreadyExistsError(ClientError):
    """Raised when attempting to create client that already exists."""
    pass


class ClientNotFoundError(ClientError):
    """Raised when client is not found."""
    pass


class ClientValidationError(ClientError):
    """Raised when client data fails validation."""
    pass


class ClientService:
    """
    Service for client operations.
    Handles business logic, validation, and audit logging.
    """
    
    def __init__(self, client_repository: ClientRepository):
        """
        Initialize ClientService.
        
        Args:
            client_repository: Repository instance for client data access
        """
        self.repository = client_repository
    
    def _validate_client_data(self, data: dict) -> None:
        """
        Validate client data.
        
        Args:
            data: Client data to validate
            
        Raises:
            ClientValidationError: If validation fails
        """
        required_fields = ["nit", "legal_name", "address", "city", "phone", "email"]
        
        for field in required_fields:
            if not data.get(field):
                raise ClientValidationError(f"Missing required field: {field}")
        
        # Validate NIT format
        if not validate_nit_format(data.get("nit", "")):
            raise ClientValidationError(
                f"Invalid NIT format. Expected: XXXXXXXXX-Y or XXXXXXXXXX"
            )
        
        # Validate email format (basic)
        email = data.get("email", "").strip().lower()
        if "@" not in email or "." not in email:
            raise ClientValidationError(f"Invalid email format: {email}")
        
        # Validate phone format (basic: at least 7 digits)
        phone = data.get("phone", "").replace(" ", "").replace("-", "")
        if not phone or len(phone) < 7:
            raise ClientValidationError(f"Invalid phone format: {data.get('phone')}")
    
    def create_client(self, data: dict, user_id: str = None) -> dict:
        """
        Create a new client.
        
        Args:
            data: Client data with required fields
            user_id: User ID creating the client (will be stored in created_by field)
            
        Returns:
            Created client document with _id
            
        Raises:
            ClientValidationError: If validation fails
            ClientAlreadyExistsError: If client with same NIT exists
            ClientError: If creation fails
        """
        try:
            # Validate data
            self._validate_client_data(data)
            
            # Normalize NIT
            normalized_nit = sanitize_nit(data["nit"])
            
            # Check if client with this NIT already exists
            existing = self.repository.find_by_nit(normalized_nit)
            if existing:
                raise ClientAlreadyExistsError(f"Client with NIT {normalized_nit} already exists")
            
            # Check if client with this email already exists
            email = data.get("email", "").strip().lower()
            existing_email = self.repository.find_by_email(email)
            if existing_email:
                raise ClientAlreadyExistsError(f"Client with email {email} already exists")
            
            # Sanitize string fields
            client_data = {
                "nit": normalized_nit,
                "legal_name": sanitize_string(data.get("legal_name", "")).strip(),
                "trade_name": sanitize_string(data.get("trade_name", "")).strip() if data.get("trade_name") else None,
                "address": sanitize_string(data.get("address", "")).strip(),
                "city": sanitize_string(data.get("city", "")).strip(),
                "phone": sanitize_string(data.get("phone", "")).strip(),
                "email": email,
                "contact_name": sanitize_string(data.get("contact_name", "")).strip() if data.get("contact_name") else None,
                "is_active": True,
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            # Insert into database
            client_id = self.repository.insert_one(client_data)
            
            # Convert ObjectId to string
            client_data["_id"] = client_id
            
            return client_data
        
        except ClientValidationError:
            raise
        except ClientAlreadyExistsError:
            raise
        except RepositoryError:
            raise
        except Exception as e:
            raise ClientError(f"Error creating client: {str(e)}") from e
    
    def get_client(self, client_id: str) -> Optional[dict]:
        """
        Get a client by ID.
        
        Args:
            client_id: Client ID as string
            
        Returns:
            Client document or None if not found
            
        Raises:
            ClientError: If operation fails
        """
        try:
            return self.repository.find_by_id(client_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise ClientError(f"Error getting client {client_id}: {str(e)}") from e
    
    def get_client_by_nit(self, nit: str) -> Optional[dict]:
        """
        Get a client by NIT.
        
        Args:
            nit: Client NIT
            
        Returns:
            Client document or None if not found
            
        Raises:
            ClientError: If operation fails
        """
        try:
            return self.repository.find_by_nit(nit)
        except RepositoryError:
            raise
        except Exception as e:
            raise ClientError(f"Error getting client by NIT {nit}: {str(e)}") from e
    
    def list_clients(
        self,
        active_only: bool = True,
        limit: int = 100,
        skip: int = 0,
        user_id: Optional[str] = None
    ) -> list[dict]:
        """
        List clients with optional filtering.
        
        Args:
            active_only: If True, only return active clients
            limit: Maximum number of results
            skip: Pagination offset
            user_id: If provided, filter by created_by (ownership-based)
            
        Returns:
            List of client documents
            
        Raises:
            ClientError: If operation fails
        """
        try:
            # Apply ownership filter if user_id provided
            if user_id:
                if active_only:
                    return self.repository.find_many(
                        {"created_by": user_id, "is_active": True},
                        limit=limit,
                        skip=skip,
                        sort=[("created_at", -1)]
                    )
                else:
                    return self.repository.find_many(
                        {"created_by": user_id},
                        limit=limit,
                        skip=skip,
                        sort=[("created_at", -1)]
                    )
            else:
                if active_only:
                    return self.repository.find_active(limit=limit, skip=skip)
                else:
                    return self.repository.find_many({}, limit=limit, skip=skip)
        except RepositoryError:
            raise
        except Exception as e:
            raise ClientError(f"Error listing clients: {str(e)}") from e
    
    def update_client(self, client_id: str, data: dict) -> dict:
        """
        Update client data.
        
        Args:
            client_id: Client ID as string
            data: Fields to update
            
        Returns:
            Updated client document
            
        Raises:
            ClientValidationError: If validation fails
            ClientNotFoundError: If client not found
            ClientError: If operation fails
        """
        try:
            # Get existing client
            existing = self.repository.find_by_id(client_id)
            if not existing:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            # If NIT is being updated, check for duplicate
            if data.get("nit") and data["nit"] != existing.get("nit"):
                normalized_new_nit = sanitize_nit(data["nit"])
                duplicate = self.repository.find_by_nit(normalized_new_nit)
                if duplicate:
                    raise ClientAlreadyExistsError(
                        f"Client with NIT {normalized_new_nit} already exists"
                    )
                data["nit"] = normalized_new_nit
            
            # If email is being updated, check for duplicate
            if data.get("email") and data["email"].lower() != existing.get("email", "").lower():
                email_lower = data["email"].lower().strip()
                duplicate = self.repository.find_by_email(email_lower)
                if duplicate:
                    raise ClientAlreadyExistsError(f"Client with email {email_lower} already exists")
                data["email"] = email_lower
            
            # Sanitize string fields
            update_data = {}
            if data.get("nit"):
                update_data["nit"] = sanitize_nit(data["nit"])
            if data.get("legal_name"):
                update_data["legal_name"] = sanitize_string(data.get("legal_name")).strip()
            if data.get("trade_name"):
                update_data["trade_name"] = sanitize_string(data.get("trade_name")).strip() if data.get("trade_name") else None
            if data.get("address"):
                update_data["address"] = sanitize_string(data.get("address")).strip()
            if data.get("city"):
                update_data["city"] = sanitize_string(data.get("city")).strip()
            if data.get("phone"):
                update_data["phone"] = sanitize_string(data.get("phone")).strip()
            if data.get("email"):
                update_data["email"] = data.get("email").lower().strip()
            if data.get("contact_name"):
                update_data["contact_name"] = sanitize_string(data.get("contact_name")).strip() if data.get("contact_name") else None
            
            # Update in database
            success = self.repository.update(client_id, update_data)
            if not success:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            # Fetch and return updated client
            updated = self.repository.find_by_id(client_id)
            return updated
        
        except ClientValidationError:
            raise
        except ClientAlreadyExistsError:
            raise
        except ClientNotFoundError:
            raise
        except RepositoryError:
            raise
        except Exception as e:
            raise ClientError(f"Error updating client {client_id}: {str(e)}") from e
    
    def delete_client(self, client_id: str) -> bool:
        """
        Delete a client (soft delete - sets is_active to False).
        
        Args:
            client_id: Client ID as string
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            ClientError: If operation fails
        """
        try:
            return self.repository.soft_delete(client_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise ClientError(f"Error deleting client {client_id}: {str(e)}") from e
