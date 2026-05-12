"""
Company service - business logic layer for company operations.

Includes audit logging for all write operations (CREATE, UPDATE, DELETE).
"""
from typing import Optional
from datetime import datetime, timezone
import logging

from src.repositories.company_repository import CompanyRepository, RepositoryError
from src.domain.company import sanitize_nit, validate_nit_format, company_from_dict
from src.infrastructure.sanitizer import sanitize_string
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class CompanyError(Exception):
    """Base exception for company service errors."""
    pass


class CompanyAlreadyExistsError(CompanyError):
    """Raised when attempting to create company that already exists."""
    pass


class CompanyNotFoundError(CompanyError):
    """Raised when company is not found."""
    pass


class CompanyValidationError(CompanyError):
    """Raised when company data fails validation."""
    pass


class CompanyService:
    """
    Service for company operations.
    Handles business logic, validation, and audit logging.
    """
    
    def __init__(self, company_repository: CompanyRepository, audit_service: Optional[AuditService] = None):
        """
        Initialize CompanyService.
        
        Args:
            company_repository: Repository instance for company data access
            audit_service: Optional AuditService for audit logging
        """
        self.repository = company_repository
        self.audit_service = audit_service
    
    def _validate_company_data(self, data: dict) -> None:
        """
        Validate company data.
        
        Args:
            data: Company data to validate
            
        Raises:
            CompanyValidationError: If validation fails
        """
        required_fields = ["nit", "legal_name", "address", "city", "phone", "email"]
        
        for field in required_fields:
            if not data.get(field):
                raise CompanyValidationError(f"Missing required field: {field}")
        
        # Validate NIT format
        if not validate_nit_format(data.get("nit", "")):
            raise CompanyValidationError(
                f"Invalid NIT format. Expected: XXXXXXXXX-Y or XXXXXXXXXX"
            )
        
        # Validate email format (basic)
        email = data.get("email", "").strip().lower()
        if "@" not in email or "." not in email:
            raise CompanyValidationError(f"Invalid email format: {email}")
        
        # Validate phone format (basic: at least 7 digits)
        phone = data.get("phone", "").replace(" ", "").replace("-", "")
        if not phone or len(phone) < 7:
            raise CompanyValidationError(f"Invalid phone format: {data.get('phone')}")
    
    def create_company(self, data: dict, user_id: Optional[str] = None, ip_address: Optional[str] = None, endpoint: Optional[str] = None) -> dict:
        """
        Create a new company with audit logging.
        
        Args:
            data: Company data with required fields
            user_id: ID of user creating the company (optional)
            ip_address: Client IP address (optional)
            endpoint: API endpoint that triggered the creation (optional)
            
        Returns:
            Created company document with _id
            
        Raises:
            CompanyValidationError: If validation fails
            CompanyAlreadyExistsError: If company with same NIT exists
            CompanyError: If creation fails
        """
        try:
            # Validate data
            self._validate_company_data(data)
            
            # Normalize NIT
            normalized_nit = sanitize_nit(data["nit"])
            
            # Check if company with this NIT already exists
            existing = self.repository.find_by_nit(normalized_nit)
            if existing:
                raise CompanyAlreadyExistsError(f"Company with NIT {normalized_nit} already exists")
            
            # Check if company with this email already exists
            email = data.get("email", "").strip().lower()
            existing_email = self.repository.find_by_email(email)
            if existing_email:
                raise CompanyAlreadyExistsError(f"Company with email {email} already exists")
            
            # Sanitize string fields
            company_data = {
                "nit": normalized_nit,
                "legal_name": sanitize_string(data.get("legal_name", "")).strip(),
                "trade_name": sanitize_string(data.get("trade_name", "")).strip() if data.get("trade_name") else None,
                "address": sanitize_string(data.get("address", "")).strip(),
                "city": sanitize_string(data.get("city", "")).strip(),
                "phone": sanitize_string(data.get("phone", "")).strip(),
                "email": email,
                "contact_name": sanitize_string(data.get("contact_name", "")).strip() if data.get("contact_name") else None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            # Insert into database
            company_id = self.repository.insert_one(company_data)
            
            # Convert ObjectId to string
            company_data["_id"] = company_id
            
            # Log audit: INSERT action with new_state, previous_state=None
            if self.audit_service:
                try:
                    self.audit_service.log_action(
                        collection_name='companies',
                        document_id=company_id,
                        action='INSERT',
                        user_id=user_id,
                        previous_state=None,
                        new_state=company_data,
                        ip_address=ip_address,
                        endpoint=endpoint
                    )
                except Exception as e:
                    logger.error(f"Audit logging failed for company creation: {str(e)}")
            
            return company_data
            
        except (CompanyValidationError, CompanyAlreadyExistsError):
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error during company creation: {str(e)}")
    
    def get_company(self, company_id: str) -> dict:
        """
        Get company by ID (read-only, no audit needed).
        
        Args:
            company_id: Company ID
            
        Returns:
            Company document
            
        Raises:
            CompanyNotFoundError: If company not found
            CompanyError: If retrieval fails
        """
        try:
            company = self.repository.find_by_id(company_id)
            if not company:
                raise CompanyNotFoundError(f"Company {company_id} not found")
            return company
        except CompanyNotFoundError:
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error retrieving company: {str(e)}")
    
    def get_company_by_nit(self, nit: str) -> Optional[dict]:
        """
        Get company by NIT (read-only, no audit needed).
        
        Args:
            nit: Company NIT (with or without formatting)
            
        Returns:
            Company document or None if not found
            
        Raises:
            CompanyError: If retrieval fails
        """
        try:
            return self.repository.find_by_nit(nit)
        except RepositoryError as e:
            raise CompanyError(f"Database error retrieving company by NIT: {str(e)}")
    
    def list_companies(
        self,
        active_only: bool = True,
        limit: int = 100,
        skip: int = 0
    ) -> list[dict]:
        """
        List companies with optional filtering (read-only, no audit needed).
        
        Args:
            active_only: If True, return only active companies (default True)
            limit: Maximum results to return (default 100, max 1000)
            skip: Number of results to skip (default 0)
            
        Returns:
            List of company documents
            
        Raises:
            CompanyError: If listing fails
        """
        try:
            # Limit max results for performance
            limit = min(limit, 1000)
            
            if active_only:
                return self.repository.find_active(limit=limit, skip=skip)
            else:
                return self.repository.find_many({}, limit=limit, skip=skip)
        except RepositoryError as e:
            raise CompanyError(f"Database error listing companies: {str(e)}")
    
    def update_company(self, company_id: str, data: dict, user_id: Optional[str] = None, ip_address: Optional[str] = None, endpoint: Optional[str] = None) -> dict:
        """
        Update company data with audit logging.
        
        Args:
            company_id: Company ID
            data: Fields to update
            user_id: ID of user performing the update (optional)
            ip_address: Client IP address (optional)
            endpoint: API endpoint that triggered the update (optional)
            
        Returns:
            Updated company document
            
        Raises:
            CompanyNotFoundError: If company not found
            CompanyValidationError: If updated NIT/email conflicts with another company
            CompanyError: If update fails
        """
        try:
            # Get current company (before state)
            company = self.repository.find_by_id(company_id)
            if not company:
                raise CompanyNotFoundError(f"Company {company_id} not found")
            
            previous_state = dict(company)  # Snapshot before changes
            
            # Validate NIT if being changed
            if "nit" in data:
                if not validate_nit_format(data["nit"]):
                    raise CompanyValidationError("Invalid NIT format")
                
                normalized_nit = sanitize_nit(data["nit"])
                # Check if new NIT conflicts with another company
                existing = self.repository.find_by_nit(normalized_nit)
                if existing and str(existing.get("_id")) != str(company_id):
                    raise CompanyValidationError(f"NIT {normalized_nit} already in use")
                data["nit"] = normalized_nit
            
            # Sanitize string fields
            update_data = {}
            for key, value in data.items():
                if key in ["legal_name", "address", "city", "phone", "trade_name", "contact_name"]:
                    update_data[key] = sanitize_string(value).strip() if value else None
                elif key == "email":
                    update_data[key] = value.strip().lower()
                elif key not in ["_id", "created_at"]:  # Don't allow updating _id or created_at
                    update_data[key] = value
            
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            # Update company
            success = self.repository.update(company_id, update_data)
            if not success:
                raise CompanyError(f"Failed to update company {company_id}")
            
            # Retrieve updated company (after state)
            updated = self.repository.find_by_id(company_id)
            
            # Log audit: UPDATE action with both previous and new state
            if self.audit_service:
                try:
                    self.audit_service.log_action(
                        collection_name='companies',
                        document_id=company_id,
                        action='UPDATE',
                        user_id=user_id,
                        previous_state=previous_state,
                        new_state=updated,
                        ip_address=ip_address,
                        endpoint=endpoint,
                        details={'updated_fields': list(update_data.keys())}
                    )
                except Exception as e:
                    logger.error(f"Audit logging failed for company update: {str(e)}")
            
            return updated
            
        except (CompanyNotFoundError, CompanyValidationError, CompanyError):
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error updating company: {str(e)}")
    
    def delete_company(self, company_id: str, user_id: Optional[str] = None, ip_address: Optional[str] = None, endpoint: Optional[str] = None) -> bool:
        """
        Soft delete a company with audit logging (mark as inactive).
        
        Args:
            company_id: Company ID
            user_id: ID of user performing the deletion (optional)
            ip_address: Client IP address (optional)
            endpoint: API endpoint that triggered the deletion (optional)
            
        Returns:
            True if deleted successfully
            
        Raises:
            CompanyNotFoundError: If company not found
            CompanyError: If deletion fails
        """
        try:
            # Get company before deletion
            company = self.repository.find_by_id(company_id)
            if not company:
                raise CompanyNotFoundError(f"Company {company_id} not found")
            
            previous_state = dict(company)
            
            # Soft delete
            success = self.repository.soft_delete(company_id)
            if not success:
                raise CompanyError(f"Failed to delete company {company_id}")
            
            # Get company after soft delete
            deleted = self.repository.find_by_id(company_id)
            
            # Log audit: SOFT_DELETE action with both states
            if self.audit_service:
                try:
                    self.audit_service.log_action(
                        collection_name='companies',
                        document_id=company_id,
                        action='SOFT_DELETE',
                        user_id=user_id,
                        previous_state=previous_state,
                        new_state=deleted,
                        ip_address=ip_address,
                        endpoint=endpoint
                    )
                except Exception as e:
                    logger.error(f"Audit logging failed for company deletion: {str(e)}")
            
            return success
            
        except (CompanyNotFoundError, CompanyError):
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error deleting company: {str(e)}")
    
    def create_company(self, data: dict) -> dict:
        """
        Create a new company.
        
        Args:
            data: Company data with required fields
            
        Returns:
            Created company document with _id
            
        Raises:
            CompanyValidationError: If validation fails
            CompanyAlreadyExistsError: If company with same NIT exists
            CompanyError: If creation fails
        """
        try:
            # Validate data
            self._validate_company_data(data)
            
            # Normalize NIT
            normalized_nit = sanitize_nit(data["nit"])
            
            # Check if company with this NIT already exists
            existing = self.repository.find_by_nit(normalized_nit)
            if existing:
                raise CompanyAlreadyExistsError(f"Company with NIT {normalized_nit} already exists")
            
            # Check if company with this email already exists
            email = data.get("email", "").strip().lower()
            existing_email = self.repository.find_by_email(email)
            if existing_email:
                raise CompanyAlreadyExistsError(f"Company with email {email} already exists")
            
            # Sanitize string fields
            company_data = {
                "nit": normalized_nit,
                "legal_name": sanitize_string(data.get("legal_name", "")).strip(),
                "trade_name": sanitize_string(data.get("trade_name", "")).strip() if data.get("trade_name") else None,
                "address": sanitize_string(data.get("address", "")).strip(),
                "city": sanitize_string(data.get("city", "")).strip(),
                "phone": sanitize_string(data.get("phone", "")).strip(),
                "email": email,
                "contact_name": sanitize_string(data.get("contact_name", "")).strip() if data.get("contact_name") else None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            # Insert into database
            company_id = self.repository.insert_one(company_data)
            
            # Convert ObjectId to string
            company_data["_id"] = company_id
            
            return company_data
            
        except (CompanyValidationError, CompanyAlreadyExistsError):
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error during company creation: {str(e)}")
    
    def get_company(self, company_id: str) -> dict:
        """
        Get company by ID.
        
        Args:
            company_id: Company ID
            
        Returns:
            Company document
            
        Raises:
            CompanyNotFoundError: If company not found
            CompanyError: If retrieval fails
        """
        try:
            company = self.repository.find_by_id(company_id)
            if not company:
                raise CompanyNotFoundError(f"Company {company_id} not found")
            return company
        except CompanyNotFoundError:
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error retrieving company: {str(e)}")
    
    def get_company_by_nit(self, nit: str) -> Optional[dict]:
        """
        Get company by NIT.
        
        Args:
            nit: Company NIT (with or without formatting)
            
        Returns:
            Company document or None if not found
            
        Raises:
            CompanyError: If retrieval fails
        """
        try:
            return self.repository.find_by_nit(nit)
        except RepositoryError as e:
            raise CompanyError(f"Database error retrieving company by NIT: {str(e)}")
    
    def list_companies(
        self,
        active_only: bool = True,
        limit: int = 100,
        skip: int = 0
    ) -> list[dict]:
        """
        List companies with optional filtering.
        
        Args:
            active_only: If True, return only active companies (default True)
            limit: Maximum results to return (default 100, max 1000)
            skip: Number of results to skip (default 0)
            
        Returns:
            List of company documents
            
        Raises:
            CompanyError: If listing fails
        """
        try:
            # Limit max results for performance
            limit = min(limit, 1000)
            
            if active_only:
                return self.repository.find_active(limit=limit, skip=skip)
            else:
                return self.repository.find_many({}, limit=limit, skip=skip)
        except RepositoryError as e:
            raise CompanyError(f"Database error listing companies: {str(e)}")
    
    def update_company(self, company_id: str, data: dict) -> dict:
        """
        Update company data.
        
        Args:
            company_id: Company ID
            data: Fields to update
            
        Returns:
            Updated company document
            
        Raises:
            CompanyNotFoundError: If company not found
            CompanyValidationError: If updated NIT/email conflicts with another company
            CompanyError: If update fails
        """
        try:
            # Get current company
            company = self.repository.find_by_id(company_id)
            if not company:
                raise CompanyNotFoundError(f"Company {company_id} not found")
            
            # Validate NIT if being changed
            if "nit" in data:
                if not validate_nit_format(data["nit"]):
                    raise CompanyValidationError("Invalid NIT format")
                
                normalized_nit = sanitize_nit(data["nit"])
                # Check if new NIT conflicts with another company
                existing = self.repository.find_by_nit(normalized_nit)
                if existing and existing.get("_id") != company_id:
                    raise CompanyValidationError(f"NIT {normalized_nit} already in use")
                data["nit"] = normalized_nit
            
            # Sanitize string fields
            update_data = {}
            for key, value in data.items():
                if key in ["legal_name", "address", "city", "phone", "trade_name", "contact_name"]:
                    update_data[key] = sanitize_string(value).strip() if value else None
                elif key == "email":
                    update_data[key] = value.strip().lower()
                elif key not in ["_id", "created_at"]:  # Don't allow updating _id or created_at
                    update_data[key] = value
            
            # Update company
            success = self.repository.update(company_id, update_data)
            if not success:
                raise CompanyError(f"Failed to update company {company_id}")
            
            # Retrieve and return updated company
            updated = self.repository.find_by_id(company_id)
            return updated
            
        except (CompanyNotFoundError, CompanyValidationError, CompanyError):
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error updating company: {str(e)}")
    
    def delete_company(self, company_id: str) -> bool:
        """
        Soft delete a company (mark as inactive).
        
        Args:
            company_id: Company ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            CompanyNotFoundError: If company not found
            CompanyError: If deletion fails
        """
        try:
            # Verify company exists
            company = self.repository.find_by_id(company_id)
            if not company:
                raise CompanyNotFoundError(f"Company {company_id} not found")
            
            # Soft delete
            success = self.repository.soft_delete(company_id)
            if not success:
                raise CompanyError(f"Failed to delete company {company_id}")
            
            return success
            
        except (CompanyNotFoundError, CompanyError):
            raise
        except RepositoryError as e:
            raise CompanyError(f"Database error deleting company: {str(e)}")
