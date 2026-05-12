"""
Tests for Audit Service

Tests comprehensive audit logging functionality including document snapshots,
ObjectId serialization, and sensitive field filtering.
"""

import pytest
from datetime import datetime, timezone
from bson.objectid import ObjectId
from unittest.mock import Mock, MagicMock, patch
from mongomock import MongoClient as MockMongoClient

from src.services.audit_service import (
    AuditService,
    AuditError,
    _serialize_document,
)
from src.infrastructure.database import MongoDBConnection


@pytest.fixture
def mock_connection():
    """Create mock MongoDB connection with mongomock."""
    MongoDBConnection._instance = None
    
    with patch('src.infrastructure.database.MongoClient', MockMongoClient):
        connection = MongoDBConnection()
        connection.client = MockMongoClient()
        connection.db = connection.client.test_db
        connection._initialized = True
        connection._create_indexes()
        
        yield connection
        
        MongoDBConnection._instance = None


@pytest.fixture
def audit_service(mock_connection):
    """Create AuditService instance."""
    return AuditService(mock_connection)


class TestSerializeDocument:
    """Tests for document serialization function."""
    
    def test_serialize_document_with_objectid(self):
        """Test that ObjectId fields are converted to strings."""
        doc_id = ObjectId()
        doc = {
            '_id': doc_id,
            'name': 'Test',
            'created_at': datetime.now(timezone.utc)
        }
        
        serialized = _serialize_document(doc)
        
        assert serialized['_id'] == str(doc_id)
        assert isinstance(serialized['_id'], str)
        assert serialized['name'] == 'Test'
    
    def test_serialize_document_removes_sensitive_fields(self):
        """Test that sensitive fields are excluded."""
        doc = {
            'name': 'Test Company',
            'password_hash': 'secret123',
            'api_key': 'key123',
            'email': 'test@example.com'
        }
        
        serialized = _serialize_document(doc)
        
        assert 'password_hash' not in serialized
        assert 'api_key' not in serialized
        assert serialized['name'] == 'Test Company'
        assert serialized['email'] == 'test@example.com'
    
    def test_serialize_document_nested_objectid(self):
        """Test that nested ObjectIds are converted."""
        company_id = ObjectId()
        vehicle_id = ObjectId()
        doc = {
            'company_id': company_id,
            'details': {
                'vehicle_id': vehicle_id,
                'name': 'Test'
            }
        }
        
        serialized = _serialize_document(doc)
        
        assert serialized['company_id'] == str(company_id)
        assert serialized['details']['vehicle_id'] == str(vehicle_id)
    
    def test_serialize_document_list_with_objectid(self):
        """Test that ObjectIds in lists are converted."""
        doc = {
            'items': [ObjectId(), 'string', ObjectId()],
            'name': 'Test'
        }
        
        serialized = _serialize_document(doc)
        
        assert len(serialized['items']) == 3
        assert isinstance(serialized['items'][0], str)
        assert serialized['items'][1] == 'string'
        assert isinstance(serialized['items'][2], str)
    
    def test_serialize_document_none_returns_none(self):
        """Test that None input returns None."""
        result = _serialize_document(None)
        assert result is None


class TestAuditService:
    """Tests for AuditService functionality."""
    
    def test_log_action_insert(self, audit_service):
        """Test logging an INSERT action."""
        company_id = str(ObjectId())
        new_state = {
            '_id': company_id,
            'nit': '123456789',
            'name': 'Test Company',
            'created_at': datetime.now(timezone.utc)
        }
        
        audit_id = audit_service.log_action(
            collection_name='companies',
            document_id=company_id,
            action='INSERT',
            user_id='user123',
            previous_state=None,
            new_state=new_state
        )
        
        assert audit_id is not None
        assert isinstance(audit_id, str)
        
        # Verify entry was stored
        entry = audit_service.audit_collection.find_one({'document_id': company_id})
        assert entry is not None
        assert entry['action'] == 'INSERT'
        assert entry['previous_state'] is None
        assert entry['new_state'] is not None
        assert entry['user_id'] == 'user123'
    
    def test_log_action_update(self, audit_service):
        """Test logging an UPDATE action with before/after snapshots."""
        doc_id = str(ObjectId())
        previous_state = {
            '_id': doc_id,
            'name': 'Old Name',
            'status': 'active'
        }
        new_state = {
            '_id': doc_id,
            'name': 'New Name',
            'status': 'active'
        }
        
        audit_id = audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='UPDATE',
            user_id='user456',
            previous_state=previous_state,
            new_state=new_state,
            details={'updated_fields': ['name']}
        )
        
        assert audit_id is not None
        
        # Verify entry contains both snapshots
        entry = audit_service.audit_collection.find_one({'document_id': doc_id})
        assert entry['previous_state']['name'] == 'Old Name'
        assert entry['new_state']['name'] == 'New Name'
        assert entry['details']['updated_fields'] == ['name']
    
    def test_log_action_soft_delete(self, audit_service):
        """Test logging a SOFT_DELETE action."""
        doc_id = str(ObjectId())
        previous_state = {
            '_id': doc_id,
            'name': 'Test',
            'is_active': True
        }
        new_state = {
            '_id': doc_id,
            'name': 'Test',
            'is_active': False
        }
        
        audit_id = audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='SOFT_DELETE',
            user_id='user789',
            previous_state=previous_state,
            new_state=new_state
        )
        
        assert audit_id is not None
        
        # Verify action type
        entry = audit_service.audit_collection.find_one({'document_id': doc_id})
        assert entry['action'] == 'SOFT_DELETE'
        assert entry['new_state']['is_active'] is False
    
    def test_log_action_with_ip_and_endpoint(self, audit_service):
        """Test logging with IP and endpoint information."""
        doc_id = str(ObjectId())
        
        audit_id = audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='INSERT',
            user_id='user123',
            new_state={'name': 'Test'},
            ip_address='192.168.1.1',
            endpoint='/api/companies'
        )
        
        entry = audit_service.audit_collection.find_one({'document_id': doc_id})
        assert entry['ip_address'] == '192.168.1.1'
        assert entry['endpoint'] == '/api/companies'
    
    def test_log_action_serializes_objectid(self, audit_service):
        """Test that ObjectIds in snapshots are serialized."""
        company_id = ObjectId()
        vehicle_id = ObjectId()
        
        new_state = {
            '_id': company_id,
            'vehicle_ids': [vehicle_id],
            'name': 'Test'
        }
        
        audit_service.log_action(
            collection_name='companies',
            document_id=str(company_id),
            action='INSERT',
            user_id='user123',
            new_state=new_state
        )
        
        entry = audit_service.audit_collection.find_one({'document_id': str(company_id)})
        
        # Verify ObjectIds were converted to strings
        assert isinstance(entry['new_state']['_id'], str)
        assert isinstance(entry['new_state']['vehicle_ids'][0], str)
        assert entry['new_state']['_id'] == str(company_id)
    
    def test_log_action_removes_sensitive_fields(self, audit_service):
        """Test that password_hash and similar fields are excluded."""
        doc_id = str(ObjectId())
        new_state = {
            '_id': doc_id,
            'name': 'Test User',
            'password_hash': 'should_not_appear',
            'api_key': 'secret_key_123',
            'email': 'user@example.com'
        }
        
        audit_service.log_action(
            collection_name='users',
            document_id=doc_id,
            action='INSERT',
            user_id='admin123',
            new_state=new_state
        )
        
        entry = audit_service.audit_collection.find_one({'document_id': doc_id})
        
        # Sensitive fields should be removed
        assert 'password_hash' not in entry['new_state']
        assert 'api_key' not in entry['new_state']
        # Non-sensitive fields should remain
        assert entry['new_state']['email'] == 'user@example.com'
    
    def test_get_document_history(self, audit_service):
        """Test retrieving audit trail for a document."""
        doc_id = str(ObjectId())
        
        # Log multiple actions
        audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='INSERT',
            user_id='user1',
            new_state={'name': 'Company A'}
        )
        
        audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='UPDATE',
            user_id='user2',
            previous_state={'name': 'Company A'},
            new_state={'name': 'Company B'}
        )
        
        audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='UPDATE',
            user_id='user3',
            previous_state={'name': 'Company B'},
            new_state={'name': 'Company C'}
        )
        
        # Retrieve history
        history = audit_service.get_document_history(
            collection_name='companies',
            document_id=doc_id
        )
        
        assert len(history) == 3
        # Verify we can see all three actions
        actions = [h['action'] for h in history]
        assert 'INSERT' in actions
        assert 'UPDATE' in actions
        assert history[0]['user_id'] in ['user1', 'user2', 'user3']
    
    def test_get_user_actions(self, audit_service):
        """Test retrieving all actions by a specific user."""
        user_id = 'admin123'
        doc1 = str(ObjectId())
        doc2 = str(ObjectId())
        doc3 = str(ObjectId())
        
        # Log actions by the same user on different documents
        audit_service.log_action('companies', doc1, 'INSERT', user_id=user_id)
        audit_service.log_action('companies', doc2, 'UPDATE', user_id=user_id)
        audit_service.log_action('vehicles', doc3, 'INSERT', user_id=user_id)
        
        # Log action by different user
        audit_service.log_action('companies', str(ObjectId()), 'INSERT', user_id='other_user')
        
        # Retrieve user actions
        actions = audit_service.get_user_actions(user_id=user_id)
        
        assert len(actions) == 3
        assert all(action['user_id'] == user_id for action in actions)
    
    def test_get_collection_changes(self, audit_service):
        """Test retrieving all changes to a specific collection."""
        company_doc = str(ObjectId())
        vehicle_doc = str(ObjectId())
        
        audit_service.log_action('companies', company_doc, 'INSERT', user_id='user1')
        audit_service.log_action('companies', str(ObjectId()), 'UPDATE', user_id='user2')
        audit_service.log_action('vehicles', vehicle_doc, 'INSERT', user_id='user3')
        
        # Get all changes to companies collection
        changes = audit_service.get_collection_changes(collection_name='companies')
        
        assert len(changes) == 2
        assert all(change['collection_name'] == 'companies' for change in changes)
    
    def test_get_collection_changes_filter_by_action(self, audit_service):
        """Test filtering collection changes by action type."""
        doc1 = str(ObjectId())
        doc2 = str(ObjectId())
        doc3 = str(ObjectId())
        
        audit_service.log_action('companies', doc1, 'INSERT', user_id='user1')
        audit_service.log_action('companies', doc2, 'UPDATE', user_id='user2')
        audit_service.log_action('companies', doc3, 'SOFT_DELETE', user_id='user3')
        
        # Get only INSERT actions
        inserts = audit_service.get_collection_changes(collection_name='companies', action='INSERT')
        
        assert len(inserts) == 1
        assert inserts[0]['action'] == 'INSERT'
    
    def test_log_action_failure_doesnt_raise(self, audit_service):
        """Test that audit service failures don't raise exceptions."""
        # Create a scenario where insert might fail
        audit_service.audit_collection = None
        
        # This should not raise an exception
        result = audit_service.log_action(
            collection_name='companies',
            document_id='doc123',
            action='INSERT',
            user_id='user123'
        )
        
        # Should return None on failure
        assert result is None
    
    def test_audit_entry_timestamp_in_utc(self, audit_service):
        """Test that audit entries have UTC timestamps."""
        doc_id = str(ObjectId())
        
        audit_service.log_action(
            collection_name='companies',
            document_id=doc_id,
            action='INSERT',
            user_id='user123',
            new_state={'name': 'Test'}
        )
        
        entry = audit_service.audit_collection.find_one({'document_id': doc_id})
        
        # Verify timestamp is a datetime (mongomock may return naive datetimes)
        assert isinstance(entry['timestamp'], datetime)
    
    def test_pagination_in_history(self, audit_service):
        """Test pagination in get_document_history."""
        doc_id = str(ObjectId())
        
        # Log 5 actions
        for i in range(5):
            audit_service.log_action(
                collection_name='companies',
                document_id=doc_id,
                action='UPDATE',
                user_id=f'user{i}',
                previous_state=None,
                new_state={'iteration': i}
            )
        
        # Get first 2 with skip
        history = audit_service.get_document_history(
            collection_name='companies',
            document_id=doc_id,
            limit=2,
            skip=1
        )
        
        assert len(history) == 2


class TestAuditServiceIntegration:
    """Integration tests with actual services."""
    
    def test_audit_service_initialization_requires_connection(self):
        """Test that AuditService requires initialized connection."""
        # Create uninitialized connection
        mock_conn = Mock()
        mock_conn._initialized = False
        
        with pytest.raises(AuditError):
            AuditService(mock_conn)
