"""
Base storage interface for file-based JSON persistence.
"""

import json
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from uuid import UUID

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class BaseStorage(Generic[T], ABC):
    """
    Base class for file-based JSON storage.
    
    Provides common functionality for CRUD operations on Pydantic models
    using JSON files for persistence.
    """
    
    def __init__(self, storage_dir: str, model_class: Type[T]):
        """
        Initialize storage.
        
        Args:
            storage_dir: Directory to store JSON files
            model_class: Pydantic model class for validation
        """
        self.storage_dir = Path(storage_dir)
        self.model_class = model_class
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index file if it doesn't exist
        index_file = self.storage_dir / "index.json"
        if not index_file.exists():
            with open(index_file, 'w') as f:
                json.dump({"items": [], "last_updated": datetime.utcnow().isoformat()}, f)
    
    def _get_index(self) -> Dict[str, Any]:
        """Get the index of stored items."""
        index_file = self.storage_dir / "index.json"
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"items": [], "last_updated": datetime.utcnow().isoformat()}
    
    def _update_index(self, index: Dict[str, Any]) -> None:
        """Update the index file."""
        index["last_updated"] = datetime.utcnow().isoformat()
        index_file = self.storage_dir / "index.json"
        
        # Write to temp file first, then rename for atomic operation
        temp_file = index_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(index, f, indent=2, default=str)
        temp_file.replace(index_file)
    
    def _get_file_path(self, item_id: UUID) -> Path:
        """Get file path for an item."""
        return self.storage_dir / f"{str(item_id)}.json"
    
    def _load_item(self, item_id: UUID) -> Optional[T]:
        """Load item from file."""
        file_path = self._get_file_path(item_id)
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return self.model_class(**data)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            raise StorageError(f"Failed to load item {item_id}: {str(e)}")
    
    def _save_item(self, item: T) -> None:
        """Save item to file."""
        item_id = getattr(item, 'id')
        file_path = self._get_file_path(item_id)
        
        # Update timestamps if available
        if hasattr(item, 'updated_at'):
            item.updated_at = datetime.utcnow()
        
        try:
            # Write to temp file first
            temp_file = file_path.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(item.dict(), f, indent=2, default=str)
            temp_file.replace(file_path)
            
            # Update index
            self._update_item_in_index(item)
            
        except Exception as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise StorageError(f"Failed to save item {item_id}: {str(e)}")
    
    def _update_item_in_index(self, item: T) -> None:
        """Update item entry in index."""
        item_id = str(getattr(item, 'id'))
        index = self._get_index()
        
        # Find existing entry or create new one
        item_entry = None
        for entry in index["items"]:
            if entry["id"] == item_id:
                item_entry = entry
                break
        
        if item_entry is None:
            item_entry = {"id": item_id}
            index["items"].append(item_entry)
        
        # Update common fields
        item_entry.update({
            "created_at": getattr(item, 'created_at', datetime.utcnow()).isoformat(),
            "updated_at": getattr(item, 'updated_at', datetime.utcnow()).isoformat(),
        })
        
        # Add model-specific index fields
        self._update_index_entry(item_entry, item)
        
        self._update_index(index)
    
    @abstractmethod
    def _update_index_entry(self, entry: Dict[str, Any], item: T) -> None:
        """Update index entry with model-specific fields."""
        pass
    
    def _delete_item(self, item_id: UUID) -> bool:
        """Delete item from storage."""
        file_path = self._get_file_path(item_id)
        if not file_path.exists():
            return False
        
        try:
            # Remove file
            file_path.unlink()
            
            # Remove from index
            index = self._get_index()
            index["items"] = [
                entry for entry in index["items"] 
                if entry["id"] != str(item_id)
            ]
            self._update_index(index)
            
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete item {item_id}: {str(e)}")
    
    # PUBLIC_INTERFACE
    def create(self, item: T) -> T:
        """
        Create a new item.
        
        Args:
            item: Item to create
            
        Returns:
            Created item
            
        Raises:
            StorageError: If creation fails
        """
        item_id = getattr(item, 'id')
        if self._get_file_path(item_id).exists():
            raise StorageError(f"Item {item_id} already exists")
        
        self._save_item(item)
        return item
    
    # PUBLIC_INTERFACE
    def get(self, item_id: UUID) -> Optional[T]:
        """
        Get item by ID.
        
        Args:
            item_id: Item identifier
            
        Returns:
            Item if found, None otherwise
        """
        return self._load_item(item_id)
    
    # PUBLIC_INTERFACE
    def update(self, item: T) -> T:
        """
        Update existing item.
        
        Args:
            item: Item to update
            
        Returns:
            Updated item
            
        Raises:
            StorageError: If item doesn't exist or update fails
        """
        item_id = getattr(item, 'id')
        if not self._get_file_path(item_id).exists():
            raise StorageError(f"Item {item_id} not found")
        
        self._save_item(item)
        return item
    
    # PUBLIC_INTERFACE
    def delete(self, item_id: UUID) -> bool:
        """
        Delete item by ID.
        
        Args:
            item_id: Item identifier
            
        Returns:
            True if deleted, False if not found
        """
        return self._delete_item(item_id)
    
    # PUBLIC_INTERFACE
    def list_all(self) -> List[T]:
        """
        List all items.
        
        Returns:
            List of all items
        """
        index = self._get_index()
        items = []
        
        for entry in index["items"]:
            try:
                item_id = UUID(entry["id"])
                item = self._load_item(item_id)
                if item:
                    items.append(item)
            except (ValueError, StorageError):
                # Skip invalid entries
                continue
        
        return items
    
    # PUBLIC_INTERFACE
    def search(self, filters: Dict[str, Any]) -> List[T]:
        """
        Search items with filters.
        
        Args:
            filters: Search filters
            
        Returns:
            Matching items
        """
        items = self.list_all()
        filtered_items = []
        
        for item in items:
            match = True
            for key, value in filters.items():
                if not hasattr(item, key):
                    match = False
                    break
                
                item_value = getattr(item, key)
                if isinstance(value, str) and isinstance(item_value, str):
                    # Case-insensitive string matching
                    if value.lower() not in item_value.lower():
                        match = False
                        break
                elif item_value != value:
                    match = False
                    break
            
            if match:
                filtered_items.append(item)
        
        return filtered_items
    
    # PUBLIC_INTERFACE
    def count(self) -> int:
        """
        Get total count of items.
        
        Returns:
            Number of items
        """
        index = self._get_index()
        return len(index["items"])
    
    # PUBLIC_INTERFACE
    def backup(self, backup_dir: str) -> None:
        """
        Create backup of storage.
        
        Args:
            backup_dir: Backup directory path
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy entire storage directory
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.storage_dir.name}_{timestamp}"
        final_backup_path = backup_path / backup_name
        
        shutil.copytree(self.storage_dir, final_backup_path)
    
    # PUBLIC_INTERFACE
    def restore(self, backup_path: str) -> None:
        """
        Restore storage from backup.
        
        Args:
            backup_path: Path to backup directory
        """
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            raise StorageError(f"Backup directory {backup_path} does not exist")
        
        # Remove current storage and restore from backup
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)
        
        shutil.copytree(backup_dir, self.storage_dir)
