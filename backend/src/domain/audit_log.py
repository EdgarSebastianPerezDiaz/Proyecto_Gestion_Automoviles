"""
Audit Log Domain Model

Defines the AuditLog entity and related logic
for tracking changes in the freight transport platform.
"""

from typing import TypedDict, Optional
from datetime import datetime


class AuditLogDict(TypedDict, total=False):
    """Audit Log entity representation."""
    _id: str
    timestamp: datetime
    collection_name: str  # Name of the collection being modified (e.g., 'trips', 'drivers')
    document_id: str  # ObjectId of the document as string
    action: str  # 'INSERT', 'UPDATE', 'DELETE', 'SOFT_DELETE'
    user_id: str  # User who performed the action
    previous_state: Optional[dict]  # Previous document state (for UPDATE/DELETE)
    new_state: Optional[dict]  # New document state (for INSERT/UPDATE)
    ip_address: Optional[str]  # IP address of the request origin
    endpoint: Optional[str]  # API endpoint that made the change
    details: Optional[dict]  # Additional context information


# Valid audit actions
VALID_ACTIONS = ['INSERT', 'UPDATE', 'DELETE', 'SOFT_DELETE']


def validate_action(action: str) -> bool:
    """
    Validate audit action.
    
    Args:
        action: Action code to validate
        
    Returns:
        True if valid action, False otherwise
    """
    return action in VALID_ACTIONS


def audit_log_to_dict(log_doc: dict) -> AuditLogDict:
    """
    Convert MongoDB audit log document to AuditLogDict.
    
    Args:
        log_doc: MongoDB audit log document
        
    Returns:
        AuditLogDict with all fields
    """
    return AuditLogDict(
        _id=str(log_doc.get('_id', '')),
        timestamp=log_doc.get('timestamp'),
        collection_name=log_doc.get('collection_name'),
        document_id=str(log_doc.get('document_id', '')),
        action=log_doc.get('action'),
        user_id=log_doc.get('user_id'),
        previous_state=log_doc.get('previous_state'),
        new_state=log_doc.get('new_state'),
        ip_address=log_doc.get('ip_address'),
        endpoint=log_doc.get('endpoint'),
        details=log_doc.get('details')
    )
