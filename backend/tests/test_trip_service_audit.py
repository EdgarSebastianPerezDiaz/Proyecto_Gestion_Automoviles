"""
Test trip service audit integration - INSERT, UPDATE, SOFT_DELETE actions.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from bson import ObjectId

from src.services.trip_service import TripService, TripError, TripValidationError, TripStatusTransitionError, TripNotFoundError
from src.infrastructure.database import MongoDBConnection, RepositoryError


@pytest.fixture
def mock_connection():
    """Mock MongoDB connection."""
    return Mock(spec=MongoDBConnection)


@pytest.fixture
def trip_service(mock_connection):
    """Create TripService with mocked repositories."""
    with patch('src.services.trip_service.TripRepository'), \
         patch('src.services.trip_service.VehicleRepository'), \
         patch('src.services.trip_service.DriverRepository'), \
         patch('src.services.trip_service.CargoTypeRepository'), \
         patch('src.services.trip_service.TripStatusRepository'), \
         patch('src.services.trip_service.InvoiceService'), \
         patch('src.services.trip_service.AuditService') as mock_audit:
        
        service = TripService(mock_connection)
        service.audit_service = mock_audit.return_value
        return service


class TestCreateTripAudit:
    """Test INSERT audit action in create_trip."""
    
    def test_create_trip_logs_insert_audit(self, trip_service):
        """Test that create_trip logs INSERT action with previous_state=None."""
        # Setup
        trip_id = ObjectId()
        vehicle = {'_id': ObjectId(), 'status': 'available'}
        driver = {'_id': ObjectId(), 'license_expired': False}
        cargo = {'_id': ObjectId(), 'price_per_ton': 100}
        status = {'_id': ObjectId(), 'code': 'scheduled'}
        
        trip_service.vehicle_repo.find_by_id.return_value = vehicle
        trip_service.driver_repo.find_by_id.return_value = driver
        trip_service.cargo_repo.find_by_id.return_value = cargo
        trip_service.status_repo.find_by_code.return_value = status
        trip_service.trip_repo.insert_one.return_value = trip_id
        
        data = {
            'origin': 'City A',
            'destination': 'City B',
            'departure_date': datetime.now(timezone.utc),
            'weight_tons': 10.0,
            'vehicle_id': vehicle['_id'],
            'driver_id': driver['_id'],
            'cargo_id': cargo['_id'],
            'client_id': ObjectId(),
            'recipient_id': ObjectId()
        }
        
        # Execute
        user_id = 'user123'
        result = trip_service.create_trip(data, user_id)
        
        # Verify
        assert result['_id'] == trip_id
        trip_service.audit_service.log_action.assert_called_once()
        
        call_args = trip_service.audit_service.log_action.call_args
        assert call_args[0][0] == 'trips'  # collection_name
        assert call_args[0][1] == trip_id  # document_id
        assert call_args[0][2] == 'INSERT'  # action
        assert call_args[0][3] == user_id  # user_id
        
        # Verify no previous state for INSERT
        assert call_args[1]['previous_state'] is None
        assert call_args[1]['new_state'] is not None
    
    def test_create_trip_audit_non_blocking(self, trip_service):
        """Test that audit failure doesn't break trip creation."""
        # Setup
        trip_id = ObjectId()
        vehicle = {'_id': ObjectId(), 'status': 'available'}
        driver = {'_id': ObjectId(), 'license_expired': False}
        cargo = {'_id': ObjectId(), 'price_per_ton': 100}
        status = {'_id': ObjectId(), 'code': 'scheduled'}
        
        trip_service.vehicle_repo.find_by_id.return_value = vehicle
        trip_service.driver_repo.find_by_id.return_value = driver
        trip_service.cargo_repo.find_by_id.return_value = cargo
        trip_service.status_repo.find_by_code.return_value = status
        trip_service.trip_repo.insert_one.return_value = trip_id
        
        # Make audit fail
        trip_service.audit_service.log_action.side_effect = Exception("Audit DB error")
        
        data = {
            'origin': 'City A',
            'destination': 'City B',
            'departure_date': datetime.now(timezone.utc),
            'weight_tons': 10.0,
            'vehicle_id': vehicle['_id'],
            'driver_id': driver['_id'],
            'cargo_id': cargo['_id'],
            'client_id': ObjectId(),
            'recipient_id': ObjectId()
        }
        
        # Execute - should NOT raise exception
        user_id = 'user123'
        result = trip_service.create_trip(data, user_id)
        
        # Verify trip was created despite audit failure
        assert result['_id'] == trip_id


class TestUpdateTripStatusAudit:
    """Test UPDATE audit action in update_trip_status."""
    
    def test_update_trip_status_logs_update_audit(self, trip_service):
        """Test that update_trip_status logs UPDATE action with before/after snapshots."""
        # Setup
        trip_id = ObjectId()
        trip = {
            '_id': trip_id,
            'origin': 'City A',
            'status_id': ObjectId(),
            'vehicle_id': ObjectId()
        }
        new_status = {'_id': ObjectId(), 'code': 'in_transit'}
        trip_after = dict(trip)
        trip_after['status_id'] = new_status['_id']
        
        trip_service.trip_repo.find_by_id.side_effect = [trip, trip_after]
        trip_service.status_repo.find_by_code.return_value = new_status
        
        # Mock PDF generation
        with patch.object(trip_service, '_transition_to_in_transit', return_value=trip_after):
            # Execute
            user_id = 'user456'
            result = trip_service.update_trip_status(str(trip_id), 'in_transit', user_id)
        
        # Verify
        assert result == trip_after
        trip_service.audit_service.log_action.assert_called_once()
        
        call_args = trip_service.audit_service.log_action.call_args
        assert call_args[0][0] == 'trips'  # collection_name
        assert call_args[0][2] == 'UPDATE'  # action
        assert call_args[0][3] == user_id  # user_id
        assert call_args[1]['previous_state'] == trip
        assert call_args[1]['new_state'] == trip_after
        assert call_args[1]['details']['status_transition'] == 'in_transit'
    
    def test_update_trip_status_audit_non_blocking(self, trip_service):
        """Test that audit failure doesn't break status update."""
        # Setup
        trip_id = ObjectId()
        trip = {'_id': trip_id, 'origin': 'City A', 'status_id': ObjectId()}
        new_status = {'_id': ObjectId(), 'code': 'cancelled'}
        trip_after = dict(trip)
        
        trip_service.trip_repo.find_by_id.side_effect = [trip, trip_after]
        trip_service.status_repo.find_by_code.return_value = new_status
        trip_service.audit_service.log_action.side_effect = Exception("Audit error")
        
        with patch.object(trip_service, '_transition_to_cancelled', return_value=trip_after):
            # Execute - should NOT raise
            user_id = 'user456'
            result = trip_service.update_trip_status(str(trip_id), 'cancelled', user_id)
        
        # Verify status was updated despite audit failure
        assert result == trip_after


class TestDeleteTripAudit:
    """Test SOFT_DELETE audit action in delete_trip."""
    
    def test_delete_trip_logs_soft_delete_audit(self, trip_service):
        """Test that delete_trip logs SOFT_DELETE action with before/after states."""
        # Setup
        trip_id = ObjectId()
        vehicle_id = ObjectId()
        scheduled_status = {'_id': ObjectId(), 'code': 'scheduled'}
        trip = {
            '_id': trip_id,
            'origin': 'City A',
            'vehicle_id': vehicle_id,
            'status_id': scheduled_status['_id']
        }

        trip_service.trip_repo.find_by_id.return_value = trip
        trip_service.status_repo.find_by_id.return_value = scheduled_status
        
        # Execute
        user_id = 'user789'
        trip_service.delete_trip(str(trip_id), user_id)
        
        # Verify
        trip_service.audit_service.log_action.assert_called_once()
        
        call_args = trip_service.audit_service.log_action.call_args
        assert call_args[0][0] == 'trips'  # collection_name
        assert str(call_args[0][1]) == str(trip_id)  # document_id (as string or ObjectId)
        assert call_args[0][2] == 'SOFT_DELETE'  # action
        assert call_args[0][3] == user_id  # user_id
        
        # Verify before/after states
        previous_state = call_args[1]['previous_state']
        new_state = call_args[1]['new_state']
        
        assert previous_state == trip
        assert new_state['deleted'] is True
        assert 'deleted_at' in new_state
        assert 'deleted_by' in new_state
        assert new_state['deleted_by'] == user_id
    
    def test_delete_trip_only_scheduled(self, trip_service):
        """Test that delete_trip only works on scheduled trips."""
        # Setup
        trip_id = ObjectId()
        in_transit_status = {'_id': ObjectId(), 'code': 'in_transit'}
        trip = {
            '_id': trip_id,
            'origin': 'City A',
            'vehicle_id': ObjectId(),
            'status_id': in_transit_status['_id']
        }
        
        trip_service.trip_repo.find_by_id.return_value = trip
        trip_service.status_repo.find_by_id.return_value = in_transit_status
        
        # Execute - should raise
        with pytest.raises(TripStatusTransitionError) as exc_info:
            trip_service.delete_trip(str(trip_id), 'user123')
        
        assert 'Only scheduled trips can be deleted' in str(exc_info.value)
    
    def test_delete_trip_releases_vehicle(self, trip_service):
        """Test that delete_trip releases the vehicle."""
        # Setup
        trip_id = ObjectId()
        vehicle_id = ObjectId()
        scheduled_status = {'_id': ObjectId(), 'code': 'scheduled'}
        trip = {
            '_id': trip_id,
            'origin': 'City A',
            'vehicle_id': vehicle_id,
            'status_id': scheduled_status['_id']
        }
        
        trip_service.trip_repo.find_by_id.return_value = trip
        trip_service.status_repo.find_by_id.return_value = scheduled_status
        
        # Execute
        trip_service.delete_trip(str(trip_id), 'user123')
        
        # Verify vehicle was released
        trip_service.vehicle_repo.update_one.assert_called_once()
        call_args = trip_service.vehicle_repo.update_one.call_args
        
        # Check the filter and update dict
        filter_dict = call_args[0][0]
        update_dict = call_args[0][1]
        
        assert '_id' in filter_dict
        assert update_dict.get('$set', {}).get('status') == 'available'
    
    def test_delete_trip_audit_non_blocking(self, trip_service):
        """Test that audit failure doesn't break trip deletion."""
        # Setup
        trip_id = ObjectId()
        vehicle_id = ObjectId()
        scheduled_status = {'_id': ObjectId(), 'code': 'scheduled'}
        trip = {
            '_id': trip_id,
            'origin': 'City A',
            'vehicle_id': vehicle_id,
            'status_id': scheduled_status['_id']
        }
        
        trip_service.trip_repo.find_by_id.return_value = trip
        trip_service.status_repo.find_by_id.return_value = scheduled_status
        trip_service.audit_service.log_action.side_effect = Exception("Audit error")
        
        # Execute - should NOT raise
        trip_service.delete_trip(str(trip_id), 'user123')
        
        # Verify trip and vehicle were updated
        trip_service.trip_repo.update_one.assert_called_once()
        trip_service.vehicle_repo.update_one.assert_called_once()


class TestVehicleStateAudit:
    """Test vehicle state changes are audited during transitions."""
    
    def test_transition_to_in_transit_audits_vehicle(self, trip_service):
        """Test vehicle state change is audited when transitioning to in_transit."""
        # Setup
        trip_id = ObjectId()
        vehicle_id = ObjectId()
        status = {'_id': ObjectId(), 'code': 'in_transit'}
        trip = {
            '_id': trip_id,
            'origin': 'City A',
            'vehicle_id': vehicle_id,
            'status_id': ObjectId()
        }
        
        # Mock PDF generation
        with patch.object(trip_service, '_generate_and_upload_document', return_value='http://pdf.url'):
            trip_service.trip_repo.find_by_id.return_value = trip
            trip_service.status_repo.find_by_code.return_value = status
            trip_service.trip_repo.update_status.return_value = True
            
            # Execute
            user_id = 'user123'
            trip_service._transition_to_in_transit(trip, status, user_id)
            
            # Verify vehicle audit was logged
            calls = trip_service.audit_service.log_action.call_args_list
            assert len(calls) > 0
            
            vehicle_audit_call = calls[0]
            assert vehicle_audit_call[0][0] == 'vehicles'  # collection_name
            assert vehicle_audit_call[0][1] == vehicle_id  # document_id
            assert vehicle_audit_call[0][2] == 'UPDATE'  # action
            assert 'in_trip' in vehicle_audit_call[1]['details']['status_transition']
