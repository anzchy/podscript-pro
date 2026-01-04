"""
History Manager module for managing transcription history records.

This module provides a HistoryManager class that handles CRUD operations
on the history.json file with file locking for concurrent access safety.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from filelock import FileLock

from .models import (
    HistoryIndex,
    HistoryRecord,
    HistoryStatus,
)

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages the history.json file with thread-safe file locking.

    The history file stores an index of all completed transcription tasks,
    enabling the frontend to display a history list with metadata.
    """

    def __init__(self, history_path: Path):
        """
        Initialize the HistoryManager.

        Args:
            history_path: Path to the history.json file
        """
        self.history_path = Path(history_path)
        self.lock_path = Path(f"{history_path}.lock")

    def _get_lock(self) -> FileLock:
        """Get a file lock for thread-safe operations."""
        return FileLock(self.lock_path, timeout=10)

    def load(self) -> HistoryIndex:
        """
        Load the history index from file.

        Returns:
            HistoryIndex object (empty if file doesn't exist)
        """
        with self._get_lock():
            if not self.history_path.exists():
                return HistoryIndex(
                    version="1.0",
                    updated_at=datetime.now(timezone.utc),
                    records=[]
                )

            try:
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                return HistoryIndex.model_validate(data)
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"Failed to load history file: {e}")
                # Return empty index on error, don't crash
                return HistoryIndex(
                    version="1.0",
                    updated_at=datetime.now(timezone.utc),
                    records=[]
                )

    def save(self, index: HistoryIndex) -> None:
        """
        Save the history index to file.

        Args:
            index: HistoryIndex object to save
        """
        with self._get_lock():
            # Ensure parent directory exists
            self.history_path.parent.mkdir(parents=True, exist_ok=True)

            # Update timestamp
            index.updated_at = datetime.now(timezone.utc)

            # Write with pretty formatting for debugging
            data = index.model_dump(mode="json")
            self.history_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8"
            )

    def add_record(self, record: HistoryRecord) -> None:
        """
        Add a new record to the history.

        Records are added at the beginning (most recent first).

        Args:
            record: HistoryRecord to add
        """
        index = self.load()

        # Check for duplicate task_id
        existing_ids = {r.task_id for r in index.records}
        if record.task_id in existing_ids:
            logger.warning(f"Record with task_id {record.task_id} already exists, skipping")
            return

        # Add to beginning (most recent first)
        index.records.insert(0, record)
        self.save(index)
        logger.info(f"Added history record: {record.task_id}")

    def get_record(self, task_id: str) -> Optional[HistoryRecord]:
        """
        Get a single record by task_id.

        Args:
            task_id: The task ID to look up

        Returns:
            HistoryRecord if found, None otherwise
        """
        index = self.load()
        for record in index.records:
            if record.task_id == task_id:
                return record
        return None

    def update_record(self, task_id: str, **kwargs) -> bool:
        """
        Update a record's fields.

        Args:
            task_id: The task ID to update
            **kwargs: Fields to update (viewed, tags, status, etc.)

        Returns:
            True if updated, False if not found
        """
        index = self.load()

        for i, record in enumerate(index.records):
            if record.task_id == task_id:
                # Update only provided fields
                record_data = record.model_dump()
                for key, value in kwargs.items():
                    if key in record_data and value is not None:
                        record_data[key] = value

                # Re-validate and update
                index.records[i] = HistoryRecord.model_validate(record_data)
                self.save(index)
                logger.info(f"Updated history record: {task_id}")
                return True

        logger.warning(f"Record not found for update: {task_id}")
        return False

    def delete_record(self, task_id: str) -> bool:
        """
        Soft delete a record by setting status to DELETED.

        The record remains in history.json but is filtered from normal queries.

        Args:
            task_id: The task ID to delete

        Returns:
            True if deleted, False if not found
        """
        return self.update_record(task_id, status=HistoryStatus.DELETED)

    def list_records(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        include_deleted: bool = False
    ) -> Tuple[List[HistoryRecord], int]:
        """
        List records with pagination and optional filtering.

        Args:
            page: Page number (1-indexed)
            limit: Records per page (max 100)
            status: Optional status filter
            include_deleted: Whether to include deleted records (default: False)

        Returns:
            Tuple of (records list, total count)
        """
        index = self.load()

        # Filter records
        filtered = []
        for record in index.records:
            # Skip deleted unless explicitly requested
            if not include_deleted and record.status == HistoryStatus.DELETED:
                continue

            # Apply status filter if specified
            if status and record.status.value != status:
                continue

            filtered.append(record)

        total = len(filtered)

        # Apply pagination
        limit = min(limit, 100)  # Cap at 100
        start = (page - 1) * limit
        end = start + limit
        paginated = filtered[start:end]

        return paginated, total
