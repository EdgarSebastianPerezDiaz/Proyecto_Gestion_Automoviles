"""
Audit Service module - comprehensive audit logging for all operations.

Every INSERT, UPDATE, DELETE operation is logged with full document snapshots
before and after the change. This ensures complete compliance and debugging capabilities.

Schema audit_logs collection:
{
    _id: ObjectId,
    timestamp: datetime (UTC),
    collection_name: str,
    document_id: str (converted from ObjectId),
    action: str (INSERT, UPDATE, DELETE, SOFT_DELETE, STATUS_CHANGE),
    user_id: str (optional, None for system operations),
    previous_state: dict (snapshot before change),
    new_state: dict (snapshot after change),
    ip_address: str (optional),
    endpoint: str (optional),
    details: dict (additional context),
}
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId

from src.infrastructure.database import MongoDBConnection

logger = logging.getLogger(__name__)

# Fields to exclude from audit snapshots (sensitive data)
SENSITIVE_FIELDS = {'password_hash', 'password', 'secret_key', 'api_key', 'token'}

# Fields to exclude from snapshots (internal/system fields)
EXCLUDED_FIELDS = {'__v'}


def _serialize_document(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Convert ObjectId to string and remove sensitive fields from a document.
    
    Args:
        doc: Document to serialize (may contain ObjectId fields)
        
    Returns:
        Serialized document with ObjectId as string, or None if input is None
    """
    if doc is None:
        return None
    
    serialized = {}
    for key, value in doc.items():
        # Skip sensitive and excluded fields
        if key in SENSITIVE_FIELDS or key in EXCLUDED_FIELDS:
            continue
        
        # Convert ObjectId to string
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        # Recursively serialize nested documents
        elif isinstance(value, dict):
            serialized[key] = _serialize_document(value)
        # Handle lists that might contain ObjectIds
        elif isinstance(value, list):
            serialized[key] = [
                str(item) if isinstance(item, ObjectId) else item
                for item in value
            ]
        else:
            serialized[key] = value
    
    return serialized


class AuditError(Exception):
    """Base exception for audit operations."""
    pass


class AuditService:
    """Service for comprehensive audit logging with document snapshots."""
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize AuditService.
        
        Args:
            connection: MongoDBConnection instance
            
        Raises:
            AuditError: If connection is not initialized
        """
        if not connection or not connection._initialized:
            raise AuditError("MongoDBConnection must be initialized before creating AuditService")
        
        self.connection = connection
        self.audit_collection = connection.get_collection('audit_logs')
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create necessary indexes for efficient audit queries."""
        try:
            self.audit_collection.create_index('timestamp')
            self.audit_collection.create_index('collection_name')
            self.audit_collection.create_index('document_id')
            self.audit_collection.create_index('user_id')
            self.audit_collection.create_index([
                ('collection_name', 1),
                ('document_id', 1),
                ('timestamp', -1)
            ])
        except Exception as e:
            logger.warning(f"Failed to create audit indexes: {str(e)}")
    
    def log_action(
        self,
        collection_name: str,
        document_id: str,
        action: str,
        user_id: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Log a document action (INSERT, UPDATE, DELETE, etc.) with full snapshots.
        
        This method ensures that all document changes are captured with complete
        before and after snapshots for compliance and debugging purposes.
        
        Args:
            collection_name: Name of collection modified (e.g., 'companies', 'vehicles')
            document_id: ID of document (as string, will be preserved)
            action: Action type - INSERT, UPDATE, DELETE, SOFT_DELETE, or STATUS_CHANGE
            user_id: ID of user who performed action (None for system operations)
            previous_state: Full document state before change (for UPDATE/DELETE)
            new_state: Full document state after change (for INSERT/UPDATE)
            ip_address: Client IP address (optional)
            endpoint: API endpoint that triggered action (optional)
            details: Additional context info (optional)
            correlation_id: Correlation ID for tracing (optional, auto-detected if not provided)
            
        Returns:
            ID of the created audit log entry (as string)
            
        Raises:
            AuditError: If logging fails (but does not block main operation)
        """
        try:
            # Auto-detect correlation_id if not provided
            if not correlation_id:
                try:
                    from flask import g, has_request_context
                    if has_request_context() and hasattr(g, 'correlation_id'):
                        correlation_id = g.correlation_id
                except:
                    correlation_id = None
            
            # Serialize documents (remove sensitive fields, convert ObjectId)
            serialized_prev = _serialize_document(previous_state)
            serialized_new = _serialize_document(new_state)
            
            audit_entry = {
                'timestamp': datetime.now(timezone.utc),
                'collection_name': collection_name,
                'document_id': str(document_id),
                'action': action.upper(),
                'user_id': user_id,
                'previous_state': serialized_prev,
                'new_state': serialized_new,
                'ip_address': ip_address,
                'endpoint': endpoint,
                'correlation_id': correlation_id,
                'details': details or {}
            }
            
            result = self.audit_collection.insert_one(audit_entry)
            return str(result.inserted_id)
        
        except Exception as e:
            # Log the error but don't raise - auditing failures shouldn't block operations
            logger.error(
                f"Audit logging failed for {collection_name}.{document_id} ({action}): {str(e)}",
                exc_info=True
            )
            return None
    
    def get_document_history(
        self,
        collection_name: str,
        document_id: str,
        limit: int = 100,
        skip: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get audit trail (history) for a specific document.
        
        Returns all changes made to a document ordered by timestamp (newest first).
        
        Args:
            collection_name: Name of collection
            document_id: ID of document
            limit: Maximum number of entries to return
            skip: Pagination offset
            
        Returns:
            List of audit log entries for the document
            
        Raises:
            AuditError: If query fails
        """
        try:
            entries = list(
                self.audit_collection.find(
                    {
                        'collection_name': collection_name,
                        'document_id': str(document_id)
                    },
                    sort=[('timestamp', -1)],
                    limit=limit,
                    skip=skip
                )
            )
            
            # Convert ObjectId to string for response
            for entry in entries:
                entry['_id'] = str(entry['_id'])
            
            return entries
        
        except Exception as e:
            raise AuditError(f"Error retrieving document history: {str(e)}")
    
    def get_user_actions(
        self,
        user_id: str,
        limit: int = 1000,
        skip: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get all actions performed by a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of entries
            skip: Pagination offset
            
        Returns:
            List of audit log entries for the user
            
        Raises:
            AuditError: If query fails
        """
        try:
            entries = list(
                self.audit_collection.find(
                    {'user_id': user_id},
                    sort=[('timestamp', -1)],
                    limit=limit,
                    skip=skip
                )
            )
            
            # Convert ObjectId to string for response
            for entry in entries:
                entry['_id'] = str(entry['_id'])
            
            return entries
        
        except Exception as e:
            raise AuditError(f"Error retrieving user actions: {str(e)}")
    
    def get_collection_changes(
        self,
        collection_name: str,
        action: Optional[str] = None,
        limit: int = 1000,
        skip: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get all changes made to a specific collection.
        
        Args:
            collection_name: Name of collection
            action: Action type to filter by (optional)
            limit: Maximum number of entries
            skip: Pagination offset
            
        Returns:
            List of audit log entries for the collection
            
        Raises:
            AuditError: If query fails
        """
        try:
            query = {'collection_name': collection_name}
            if action:
                query['action'] = action.upper()
            
            entries = list(
                self.audit_collection.find(
                    query,
                    sort=[('timestamp', -1)],
                    limit=limit,
                    skip=skip
                )
            )
            
            # Convert ObjectId to string for response
            for entry in entries:
                entry['_id'] = str(entry['_id'])
            
            return entries
        
        except Exception as e:
            raise AuditError(f"Error retrieving collection changes: {str(e)}")
