"""
MongoDB Database Connection Module

Manages MongoDB client lifecycle and provides centralized access to database collections.
Implements a singleton pattern for connection management.

Features:
- Environment-based connection string (MONGO_URI)
- Automatic index creation for TTL-based document expiration
- Graceful connection cleanup
- Support for multiple collections
"""

import os
from typing import Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class DatabaseConnectionError(RepositoryError):
    """Exception raised when database connection fails."""
    pass


class MongoDBConnection:
    """
    Singleton MongoDB connection manager.
    
    Manages the MongoDB client and provides access to collections.
    Automatically handles index creation and connection lifecycle.
    
    Environment Variables:
        MONGO_URI: MongoDB connection string (required)
                   Example: mongodb://localhost:27017/freight-platform
    """
    
    _instance: Optional['MongoDBConnection'] = None
    
    def __init__(self):
        """Initialize the MongoDB connection manager."""
        self.client: Optional[MongoClient] = None
        self.db = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'MongoDBConnection':
        """
        Get the singleton instance of MongoDBConnection.
        
        Returns:
            MongoDBConnection: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def connect(self) -> None:
        """
        Connect to MongoDB and initialize collections with indexes.
        
        En desarrollo: Lee MONGO_URI desde archivo .env
        En producción (Lambda): Lee MONGO_URI desde SSM Parameter Store (inyectado en ambiente)
        
        Raises:
            DatabaseConnectionError: If MONGO_URI is not set or connection fails
            ServerSelectionTimeoutError: If MongoDB server is unreachable
        """
        # Load environment variables from .env file SOLO en desarrollo
        # En producción, Lambda inyecta variables desde SSM Parameter Store
        if os.getenv('FLASK_ENV', 'development') != 'production':
            load_dotenv()
        
        # Check if MONGO_URI is set before attempting connection
        mongo_uri = os.getenv("MONGO_URI")
        if mongo_uri is None or mongo_uri == "":
            raise DatabaseConnectionError(
                "MONGO_URI environment variable not set. "
                "En desarrollo: Agregar a .env. "
                "En producción: Debe estar en SSM Parameter Store."
            )
        
        try:
            # Connect to MongoDB with timeout
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Verify connection by pinging the server
            self.client.admin.command("ping")
            
            # Get default database (extracted from connection string)
            self.db = self.client.get_database()
            
            # Create indexes for known collections
            self._create_indexes()
            
            self._initialized = True
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            raise DatabaseConnectionError(
                f"Failed to connect to MongoDB at {mongo_uri}: {str(e)}"
            ) from e
        except Exception as e:
            raise DatabaseConnectionError(
                f"Unexpected error during MongoDB connection: {str(e)}"
            ) from e
    
    def _create_indexes(self) -> None:
        """
        Create necessary indexes for all collections.
        
        Indexes ensure optimal query performance and data integrity across all collections:
        
        - users: Unique email index for authentication
        - companies: Unique NIT index, compound indexes for queries
        - drivers: Unique ID number, license expiry tracking, license alerts
        - vehicles: Unique plate, status tracking, maintenance dates
        - clients: Unique NIT index
        - final_recipients: Active filtering and name-based searches
        - cargo_types: Active filtering and name lookups
        - trip_statuses: Unique status codes
        - trips: Status, dates, vehicle/driver/client references, availability checks
        - invoices: Unique invoice numbers, trip/client/status queries
        - audit_log: Timestamp tracking, collection+document auditing, user changes
        - login_log: User login history tracking
        - rate_limits: TTL index for auto-expiring rate limit blocks
        
        Runs only once during initialization. If indexes already exist, they are skipped.
        """
        if self.db is None:
            return
        
        try:
            logger.info("Creating database indexes...")
            
            # ===== USERS COLLECTION =====
            users_collection = self.db['users']
            users_collection.create_index([('email', ASCENDING)], unique=True)
            logger.info("✓ Users collection indexes created")
            
            # ===== COMPANIES COLLECTION =====
            companies_collection = self.db['companies']
            companies_collection.create_index([('nit', ASCENDING)], unique=True)
            companies_collection.create_index([('is_active', ASCENDING), ('legal_name', ASCENDING)])
            logger.info("✓ Companies collection indexes created")
            
            # ===== DRIVERS COLLECTION =====
            drivers_collection = self.db['drivers']
            drivers_collection.create_index([('id_number', ASCENDING)], unique=True)
            drivers_collection.create_index([('license_expiry', ASCENDING)])
            drivers_collection.create_index([('license_alert', ASCENDING)])
            drivers_collection.create_index([('license_expired', ASCENDING)])
            logger.info("✓ Drivers collection indexes created")
            
            # ===== VEHICLES COLLECTION =====
            vehicles_collection = self.db['vehicles']
            vehicles_collection.create_index([('plate', ASCENDING)], unique=True)
            vehicles_collection.create_index([('company_id', ASCENDING)])
            vehicles_collection.create_index([('status', ASCENDING)])
            vehicles_collection.create_index([('soat_expiry', ASCENDING)])
            vehicles_collection.create_index([('tech_review_expiry', ASCENDING)])
            logger.info("✓ Vehicles collection indexes created")
            
            # ===== CLIENTS COLLECTION =====
            clients_collection = self.db['clients']
            clients_collection.create_index([('nit', ASCENDING)], unique=True)
            logger.info("✓ Clients collection indexes created")
            
            # ===== FINAL_RECIPIENTS COLLECTION =====
            final_recipients_collection = self.db['final_recipients']
            final_recipients_collection.create_index([('name', ASCENDING)])
            final_recipients_collection.create_index([('is_active', ASCENDING)])
            logger.info("✓ Final Recipients collection indexes created")
            
            # ===== CARGO_TYPES COLLECTION =====
            cargo_types_collection = self.db['cargo_types']
            cargo_types_collection.create_index([('is_active', ASCENDING)])
            cargo_types_collection.create_index([('name', ASCENDING)])
            logger.info("✓ Cargo Types collection indexes created")
            
            # ===== TRIP_STATUSES COLLECTION =====
            trip_statuses_collection = self.db['trip_statuses']
            trip_statuses_collection.create_index([('code', ASCENDING)], unique=True)
            logger.info("✓ Trip Statuses collection indexes created")
            
            # ===== TRIPS COLLECTION =====
            trips_collection = self.db['trips']
            trips_collection.create_index([('status_id', ASCENDING)])
            trips_collection.create_index([('departure_date', ASCENDING)])
            trips_collection.create_index([('vehicle_id', ASCENDING)])
            trips_collection.create_index([('driver_id', ASCENDING)])
            trips_collection.create_index([('client_id', ASCENDING)])
            # Compound index for availability checks (scheduled trips by vehicle and date range)
            trips_collection.create_index([('vehicle_id', ASCENDING), ('departure_date', ASCENDING), ('status_id', ASCENDING)])
            logger.info("✓ Trips collection indexes created")
            
            # ===== INVOICES COLLECTION =====
            invoices_collection = self.db['invoices']
            invoices_collection.create_index([('invoice_number', ASCENDING)], unique=True)
            invoices_collection.create_index([('trip_id', ASCENDING)], unique=True)
            invoices_collection.create_index([('client_id', ASCENDING)])
            invoices_collection.create_index([('status', ASCENDING)])
            logger.info("✓ Invoices collection indexes created")
            
            # ===== AUDIT_LOG COLLECTION =====
            audit_log_collection = self.db['audit_log']
            audit_log_collection.create_index([('timestamp', DESCENDING)])
            # Compound index for finding changes to specific documents
            audit_log_collection.create_index([('collection_name', ASCENDING), ('document_id', ASCENDING)])
            audit_log_collection.create_index([('user_id', ASCENDING)])
            logger.info("✓ Audit Log collection indexes created")
            
            # ===== LOGIN_LOG COLLECTION =====
            login_log_collection = self.db['login_log']
            login_log_collection.create_index([('user_id', ASCENDING)])
            login_log_collection.create_index([('timestamp', DESCENDING)])
            logger.info("✓ Login Log collection indexes created")
            
            # ===== RATE_LIMITS COLLECTION =====
            # TTL index: documents with blocked_until in the past are auto-deleted
            rate_limits_collection = self.db['rate_limits']
            rate_limits_collection.create_index([('blocked_until', ASCENDING)], expireAfterSeconds=0)
            logger.info("✓ Rate Limits collection indexes created (TTL enabled)")
            
            # ===== TOKEN_BLACKLIST COLLECTION =====
            # TTL index for automatic invalidation of blacklisted tokens
            # Documents expire after expires_at timestamp
            token_blacklist_collection = self.db['token_blacklist']
            token_blacklist_collection.create_index([('expires_at', ASCENDING)], expireAfterSeconds=0)
            token_blacklist_collection.create_index([('user_id', ASCENDING)])
            token_blacklist_collection.create_index([('token_jti', ASCENDING)], unique=True)
            logger.info("✓ Token Blacklist collection indexes created (TTL enabled)")
            
            logger.info("✓ All database indexes created successfully")
            
        except Exception as e:
            # Log but don't fail if indexing fails (indexes might already exist)
            logger.warning(f"Warning during index creation (may already exist): {str(e)}")
    
    def get_collection(self, collection_name: str):
        """
        Get a MongoDB collection by name.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            pymongo.collection.Collection: The requested collection
            
        Raises:
            DatabaseConnectionError: If not connected to database
        """
        if not self._initialized or self.db is None:
            raise DatabaseConnectionError(
                "Database not initialized. Call connect() first."
            )
        
        return self.db[collection_name]
    
    def close(self) -> None:
        """
        Close the MongoDB connection gracefully.
        
        Should be called during application shutdown to ensure
        proper resource cleanup.
        """
        if self.client is not None:
            try:
                self.client.close()
                self._initialized = False
                self.client = None
                self.db = None
            except Exception as e:
                print(f"Warning: Error closing MongoDB connection: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        Check if database connection is active.
        
        Returns:
            bool: True if connected and initialized, False otherwise
        """
        return self._initialized and self.client is not None and self.db is not None
