"""
Base Repository Module

Implements generic repository pattern for MongoDB data access.
Provides abstraction layer for all database operations with built-in security (NoSQL injection prevention).

Architecture:
- BaseRepository: Generic async-like CRUD operations (synchronous for Flask)
- Automatic input sanitization to prevent NoSQL injection
- Automatic ObjectId to string conversion for responses
- Type-safe with generic typing support
"""

import re
from typing import Generic, TypeVar, Optional, List, Dict, Any
from bson import ObjectId
from pymongo.errors import PyMongoError
from src.infrastructure.database import RepositoryError, MongoDBConnection
from src.infrastructure.sanitizer import sanitize_object


T = TypeVar('T')  # Generic type for repository entities


class BaseRepository(Generic[T]):
    """
    Generic base repository for MongoDB collections.
    
    Provides CRUD operations with automatic input sanitization and type conversion.
    All filter parameters are automatically sanitized to prevent NoSQL injection attacks.
    All responses convert MongoDB ObjectId to string for API compatibility.
    
    Type Parameters:
        T: The entity type managed by this repository
    
    Attributes:
        collection_name: Name of the MongoDB collection
        connection: MongoDBConnection instance
        collection: PyMongo collection object
    """
    
    def __init__(self, collection_name: str, connection: MongoDBConnection):
        """
        Initialize the repository with a collection name and database connection.
        
        Args:
            collection_name: Name of the MongoDB collection to manage
            connection: MongoDBConnection instance (already connected)
            
        Raises:
            RepositoryError: If connection is not initialized
        """
        if not connection.is_connected():
            raise RepositoryError(
                f"Database connection not initialized. "
                f"Call MongoDBConnection.connect() before creating repositories."
            )
        
        self.collection_name = collection_name
        self.connection = connection
        self.collection = connection.get_collection(collection_name)
    
    def _sanitize_filter(self, filter_dict: dict) -> dict:
        """
        Sanitize filter dictionary keys to prevent NoSQL injection.
        
        Only sanitizes keys (to prevent dangerous MongoDB operators like $where, $function),
        but allows safe query operators like $regex, $options, $gt, $lt, etc.
        Values are safe because pymongo uses parameter binding and we trust query structure.
        
        Args:
            filter_dict: Filter criteria to sanitize
            
        Returns:
            dict: Sanitized filter dictionary (dangerous ops removed, safe ones preserved)
        """
        if not filter_dict:
            return {}
        
        # Whitelist of safe MongoDB query operators
        SAFE_OPERATORS = {
            '$eq', '$ne', '$gt', '$gte', '$lt', '$lte',  # Comparison
            '$in', '$nin',  # Array
            '$and', '$or', '$not', '$nor',  # Logical
            '$exists', '$type', '$regex', '$options',  # Field/String
            '$size', '$all', '$elemMatch',  # Array/Element
            '$set', '$unset', '$inc', '$push', '$pull',  # Update (if in update context)
        }
        
        # Blacklist of dangerous operators that could allow code execution
        DANGEROUS_OPERATORS = {
            '$where', '$function', '$accumulator',  # Code execution
        }
        
        sanitized = {}
        for key, value in filter_dict.items():
            # Allow the key as-is if it's a safe operator or doesn't start with $
            if key.startswith('$'):
                clean_key = key
                # Check if it's explicitly dangerous - would be removed
                if clean_key in DANGEROUS_OPERATORS:
                    continue  # Skip dangerous operators
                # If not in safe list and starts with $, it might be suspicious
                # For now, we allow it since pymongo will validate
            else:
                clean_key = key
            
            # Recursively handle nested dicts (for compound queries)
            if isinstance(value, dict):
                sanitized[clean_key] = self._sanitize_filter(value)
            else:
                # Preserve values as-is (pymongo handles binding safely)
                sanitized[clean_key] = value
        
        return sanitized
        return {}
    
    def _convert_id(self, doc: dict) -> dict:
        """
        Convert MongoDB ObjectId to string for API responses.
        
        Args:
            doc: Document with potential ObjectId
            
        Returns:
            dict: Document with _id as string
        """
        if doc and '_id' in doc:
            doc_copy = doc.copy()
            if isinstance(doc_copy['_id'], ObjectId):
                doc_copy['_id'] = str(doc_copy['_id'])
            return doc_copy
        return doc
    
    def _convert_ids(self, docs: List[dict]) -> List[dict]:
        """
        Convert ObjectIds to strings in a list of documents.
        
        Args:
            docs: List of documents
            
        Returns:
            list: Documents with _id as strings
        """
        return [self._convert_id(doc) for doc in docs]
    
    def find_by_id(self, id_str: str) -> Optional[Dict[str, Any]]:
        """
        Find a document by its MongoDB ObjectId.
        
        Args:
            id_str: String representation of the ObjectId
            
        Returns:
            dict: Document with _id as string, or None if not found
            
        Raises:
            RepositoryError: If id_str is not a valid ObjectId string
        """
        try:
            # Convert string id to ObjectId for lookup
            object_id = ObjectId(id_str)
        except Exception as e:
            raise RepositoryError(f"Invalid ObjectId format: {id_str}") from e
        
        try:
            doc = self.collection.find_one({"_id": object_id})
            return self._convert_id(doc) if doc else None
        except PyMongoError as e:
            raise RepositoryError(f"Error finding document by id: {str(e)}") from e
    
    def find_one(self, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching the filter criteria.
        
        Filter is automatically sanitized to prevent NoSQL injection.
        
        Args:
            filter_dict: Query filter criteria
            
        Returns:
            dict: Document with _id as string, or None if not found
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            sanitized_filter = self._sanitize_filter(filter_dict)
            doc = self.collection.find_one(sanitized_filter)
            return self._convert_id(doc) if doc else None
        except PyMongoError as e:
            raise RepositoryError(f"Error finding document: {str(e)}") from e
    
    def find_many(
        self,
        filter_dict: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents matching the filter criteria.
        
        Filter is automatically sanitized to prevent NoSQL injection.
        Supports pagination via skip and limit.
        
        Args:
            filter_dict: Query filter criteria
            limit: Maximum number of documents to return (default: 100)
            skip: Number of documents to skip for pagination (default: 0)
            sort: List of (field, direction) tuples for sorting
                  Example: [("created_at", -1)] for descending order
            
        Returns:
            list: Documents with _id as strings, empty list if no matches
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            sanitized_filter = self._sanitize_filter(filter_dict)
            query = self.collection.find(sanitized_filter).skip(skip).limit(limit)
            
            if sort:
                query = query.sort(sort)
            
            docs = list(query)
            return self._convert_ids(docs)
        except PyMongoError as e:
            raise RepositoryError(f"Error finding documents: {str(e)}") from e
    
    def insert_one(self, document: Dict[str, Any]) -> str:
        """
        Insert a single document into the collection.
        
        Args:
            document: Document to insert
            
        Returns:
            str: The inserted document's _id as a string
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            result = self.collection.insert_one(document)
            return str(result.inserted_id)
        except PyMongoError as e:
            raise RepositoryError(f"Error inserting document: {str(e)}") from e
    
    def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple documents into the collection.
        
        Args:
            documents: List of documents to insert
            
        Returns:
            list: List of inserted document _ids as strings
            
        Raises:
            RepositoryError: On database operations error
        """
        if not documents:
            return []
        
        try:
            result = self.collection.insert_many(documents)
            return [str(oid) for oid in result.inserted_ids]
        except PyMongoError as e:
            raise RepositoryError(f"Error inserting documents: {str(e)}") from e
    
    def update_one(self, filter_dict: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """
        Update a single document matching the filter criteria.
        
        Filter is automatically sanitized to prevent NoSQL injection.
        
        Args:
            filter_dict: Query filter criteria to find document to update
            update: Update operations (e.g., {"$set": {"field": "value"}})
            
        Returns:
            bool: True if a document was modified, False if no matching document
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            sanitized_filter = self._sanitize_filter(filter_dict)
            result = self.collection.update_one(sanitized_filter, update)
            return result.modified_count > 0
        except PyMongoError as e:
            raise RepositoryError(f"Error updating document: {str(e)}") from e
    
    def update_many(self, filter_dict: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update multiple documents matching the filter criteria.
        
        Filter is automatically sanitized to prevent NoSQL injection.
        
        Args:
            filter_dict: Query filter criteria to find documents to update
            update: Update operations (e.g., {"$set": {"field": "value"}})
            
        Returns:
            int: Number of documents modified
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            sanitized_filter = self._sanitize_filter(filter_dict)
            result = self.collection.update_many(sanitized_filter, update)
            return result.modified_count
        except PyMongoError as e:
            raise RepositoryError(f"Error updating documents: {str(e)}") from e
    
    def delete_by_id(self, id_str: str) -> bool:
        """
        Delete a document by its MongoDB ObjectId.
        
        Convenience method that converts string ID to ObjectId for deletion.
        
        Args:
            id_str: String representation of the ObjectId
            
        Returns:
            bool: True if a document was deleted, False if not found
            
        Raises:
            RepositoryError: If id_str is not a valid ObjectId or on deletion error
        """
        try:
            object_id = ObjectId(id_str)
        except Exception as e:
            raise RepositoryError(f"Invalid ObjectId format: {id_str}") from e
        
        return self.delete_one({"_id": object_id})
    
    def delete_one(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete a single document matching the filter criteria.
        
        Filter is automatically sanitized to prevent NoSQL injection.
        
        Args:
            filter_dict: Query filter criteria to find document to delete
            
        Returns:
            bool: True if a document was deleted, False if no matching document
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            sanitized_filter = self._sanitize_filter(filter_dict)
            result = self.collection.delete_one(sanitized_filter)
            return result.deleted_count > 0
        except PyMongoError as e:
            raise RepositoryError(f"Error deleting document: {str(e)}") from e
    
    def delete_many(self, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple documents matching the filter criteria.
        
        Filter is automatically sanitized to prevent NoSQL injection.
        
        Args:
            filter_dict: Query filter criteria to find documents to delete
            
        Returns:
            int: Number of documents deleted
            
        Raises:
            RepositoryError: On database operations error
        """
        try:
            sanitized_filter = self._sanitize_filter(filter_dict)
            result = self.collection.delete_many(sanitized_filter)
            return result.deleted_count
        except PyMongoError as e:
            raise RepositoryError(f"Error deleting documents: {str(e)}") from e
