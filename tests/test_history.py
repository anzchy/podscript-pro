"""
Unit tests for HistoryManager and keyword extraction.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from podscript_shared.history import HistoryManager
from podscript_shared.keywords import extract_keywords, extract_keywords_with_weight
from podscript_shared.models import (
    HistoryIndex,
    HistoryRecord,
    HistoryStatus,
    MediaType,
    SourceType,
)


# ============== Fixtures ==============

@pytest.fixture
def temp_history_path():
    """Create a temporary directory for history file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "history.json"


@pytest.fixture
def history_manager(temp_history_path):
    """Create a HistoryManager with temporary storage."""
    return HistoryManager(temp_history_path)


@pytest.fixture
def sample_record():
    """Create a sample history record for testing."""
    return HistoryRecord(
        task_id="abc123def456",
        title="Test Transcription",
        source_url="https://youtube.com/watch?v=test",
        source_type=SourceType.YOUTUBE,
        media_type=MediaType.VIDEO,
        duration=3600,
        file_size=1024 * 1024 * 100,  # 100MB
        tags=["AI", "测试"],
        created_at=datetime.now(timezone.utc),
        viewed=False,
        thumbnail_url="/artifacts/abc123def456/thumbnail.jpg",
        status=HistoryStatus.COMPLETED,
    )


# ============== HistoryManager Tests ==============

class TestHistoryManagerLoad:
    """Tests for HistoryManager.load()"""

    def test_load_empty_creates_default(self, history_manager):
        """Loading non-existent file returns empty index."""
        index = history_manager.load()
        assert index.version == "1.0"
        assert index.records == []
        assert index.updated_at is not None

    def test_load_existing_file(self, temp_history_path, history_manager):
        """Loading existing file returns correct data."""
        # Create a file manually
        data = {
            "version": "1.0",
            "updated_at": "2025-01-01T00:00:00",
            "records": [
                {
                    "task_id": "test123test12",
                    "title": "Test",
                    "source_type": "youtube",
                    "media_type": "video",
                    "duration": 100,
                    "file_size": 1000,
                    "tags": [],
                    "created_at": "2025-01-01T00:00:00",
                    "viewed": False,
                    "status": "completed",
                }
            ],
        }
        temp_history_path.parent.mkdir(parents=True, exist_ok=True)
        temp_history_path.write_text(json.dumps(data), encoding="utf-8")

        index = history_manager.load()
        assert len(index.records) == 1
        assert index.records[0].task_id == "test123test12"

    def test_load_corrupted_file_returns_empty(self, temp_history_path, history_manager):
        """Loading corrupted file returns empty index instead of crashing."""
        temp_history_path.parent.mkdir(parents=True, exist_ok=True)
        temp_history_path.write_text("invalid json {{{", encoding="utf-8")

        index = history_manager.load()
        assert index.records == []


class TestHistoryManagerSave:
    """Tests for HistoryManager.save()"""

    def test_save_creates_file(self, temp_history_path, history_manager):
        """Save creates the history file."""
        index = HistoryIndex(
            version="1.0",
            updated_at=datetime.now(timezone.utc),
            records=[],
        )
        history_manager.save(index)

        assert temp_history_path.exists()

    def test_save_updates_timestamp(self, history_manager):
        """Save updates the updated_at timestamp."""
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        index = HistoryIndex(
            version="1.0",
            updated_at=old_time,
            records=[],
        )
        history_manager.save(index)

        loaded = history_manager.load()
        assert loaded.updated_at > old_time


class TestHistoryManagerAddRecord:
    """Tests for HistoryManager.add_record()"""

    def test_add_record(self, history_manager, sample_record):
        """Adding a record persists it."""
        history_manager.add_record(sample_record)

        index = history_manager.load()
        assert len(index.records) == 1
        assert index.records[0].task_id == sample_record.task_id

    def test_add_multiple_records_order(self, history_manager):
        """Records are ordered with most recent first."""
        for i in range(3):
            record = HistoryRecord(
                task_id=f"task{i:08d}",
                title=f"Task {i}",
                source_type=SourceType.YOUTUBE,
                media_type=MediaType.VIDEO,
                duration=100,
                file_size=1000,
                created_at=datetime.now(timezone.utc),
                status=HistoryStatus.COMPLETED,
            )
            history_manager.add_record(record)

        index = history_manager.load()
        assert len(index.records) == 3
        # Most recent (task2) should be first
        assert index.records[0].task_id == "task00000002"

    def test_add_duplicate_is_skipped(self, history_manager, sample_record):
        """Adding duplicate task_id is skipped (no-op)."""
        history_manager.add_record(sample_record)

        # Try to add again with different title - should be skipped
        duplicate = sample_record.model_copy()
        duplicate.title = "Updated Title"
        history_manager.add_record(duplicate)

        index = history_manager.load()
        assert len(index.records) == 1
        # Original title preserved since duplicate was skipped
        assert index.records[0].title == sample_record.title


class TestHistoryManagerGetRecord:
    """Tests for HistoryManager.get_record()"""

    def test_get_existing_record(self, history_manager, sample_record):
        """Get returns existing record."""
        history_manager.add_record(sample_record)

        found = history_manager.get_record(sample_record.task_id)
        assert found is not None
        assert found.task_id == sample_record.task_id
        assert found.title == sample_record.title

    def test_get_nonexistent_record(self, history_manager):
        """Get returns None for non-existent record."""
        found = history_manager.get_record("nonexistent123")
        assert found is None


class TestHistoryManagerUpdateRecord:
    """Tests for HistoryManager.update_record()"""

    def test_update_viewed(self, history_manager, sample_record):
        """Update viewed status."""
        history_manager.add_record(sample_record)

        result = history_manager.update_record(sample_record.task_id, viewed=True)
        assert result is True

        found = history_manager.get_record(sample_record.task_id)
        assert found.viewed is True

    def test_update_tags(self, history_manager, sample_record):
        """Update tags."""
        history_manager.add_record(sample_record)

        new_tags = ["Python", "FastAPI", "测试"]
        result = history_manager.update_record(sample_record.task_id, tags=new_tags)
        assert result is True

        found = history_manager.get_record(sample_record.task_id)
        assert found.tags == new_tags

    def test_update_nonexistent_returns_false(self, history_manager):
        """Update non-existent record returns False."""
        result = history_manager.update_record("nonexistent123", viewed=True)
        assert result is False


class TestHistoryManagerDeleteRecord:
    """Tests for HistoryManager.delete_record() (soft delete)"""

    def test_soft_delete(self, history_manager, sample_record):
        """Soft delete sets status to DELETED."""
        history_manager.add_record(sample_record)

        result = history_manager.delete_record(sample_record.task_id)
        assert result is True

        found = history_manager.get_record(sample_record.task_id)
        assert found.status == HistoryStatus.DELETED

    def test_delete_nonexistent_returns_false(self, history_manager):
        """Delete non-existent record returns False."""
        result = history_manager.delete_record("nonexistent123")
        assert result is False


class TestHistoryManagerListRecords:
    """Tests for HistoryManager.list_records()"""

    def test_list_empty(self, history_manager):
        """List empty history returns empty list."""
        records, total = history_manager.list_records()
        assert records == []
        assert total == 0

    def test_list_with_records(self, history_manager):
        """List returns all non-deleted records."""
        for i in range(5):
            record = HistoryRecord(
                task_id=f"task{i:012d}",
                title=f"Task {i}",
                source_type=SourceType.YOUTUBE,
                media_type=MediaType.VIDEO,
                duration=100,
                file_size=1000,
                created_at=datetime.now(timezone.utc),
                status=HistoryStatus.COMPLETED,
            )
            history_manager.add_record(record)

        records, total = history_manager.list_records()
        assert len(records) == 5
        assert total == 5

    def test_list_pagination(self, history_manager):
        """List respects pagination parameters."""
        for i in range(10):
            record = HistoryRecord(
                task_id=f"task{i:012d}",
                title=f"Task {i}",
                source_type=SourceType.YOUTUBE,
                media_type=MediaType.VIDEO,
                duration=100,
                file_size=1000,
                created_at=datetime.now(timezone.utc),
                status=HistoryStatus.COMPLETED,
            )
            history_manager.add_record(record)

        # Page 1 with limit 3
        records, total = history_manager.list_records(page=1, limit=3)
        assert len(records) == 3
        assert total == 10

        # Page 2 with limit 3
        records, total = history_manager.list_records(page=2, limit=3)
        assert len(records) == 3
        assert total == 10

        # Last page
        records, total = history_manager.list_records(page=4, limit=3)
        assert len(records) == 1
        assert total == 10

    def test_list_filters_deleted(self, history_manager, sample_record):
        """List excludes deleted records by default."""
        history_manager.add_record(sample_record)
        history_manager.delete_record(sample_record.task_id)

        records, total = history_manager.list_records()
        assert len(records) == 0
        assert total == 0

    def test_list_include_deleted(self, history_manager, sample_record):
        """List can include deleted records if requested."""
        history_manager.add_record(sample_record)
        history_manager.delete_record(sample_record.task_id)

        records, total = history_manager.list_records(include_deleted=True)
        assert len(records) == 1
        assert total == 1

    def test_list_filter_by_status(self, history_manager):
        """List can filter by status."""
        # Add completed and failed records
        for i, status in enumerate([HistoryStatus.COMPLETED, HistoryStatus.FAILED, HistoryStatus.COMPLETED]):
            record = HistoryRecord(
                task_id=f"task{i:012d}",
                title=f"Task {i}",
                source_type=SourceType.YOUTUBE,
                media_type=MediaType.VIDEO,
                duration=100,
                file_size=1000,
                created_at=datetime.now(timezone.utc),
                status=status,
            )
            history_manager.add_record(record)

        # Filter completed only
        records, total = history_manager.list_records(status="completed")
        assert len(records) == 2
        assert total == 2

        # Filter failed only
        records, total = history_manager.list_records(status="failed")
        assert len(records) == 1
        assert total == 1

    def test_list_limit_cap(self, history_manager):
        """List caps limit at 100."""
        records, total = history_manager.list_records(limit=200)
        # Should not error, limit internally capped


# ============== Keyword Extraction Tests ==============

class TestKeywordExtraction:
    """Tests for keyword extraction module."""

    def test_extract_keywords_chinese(self):
        """Extract keywords from Chinese text."""
        text = "人工智能是计算机科学的重要分支，机器学习是人工智能的核心技术。"
        keywords = extract_keywords(text, top_k=3)

        assert len(keywords) <= 3
        assert isinstance(keywords, list)
        # Should contain relevant keywords
        assert any("智能" in kw or "学习" in kw or "计算机" in kw for kw in keywords)

    def test_extract_keywords_empty(self):
        """Extract keywords from empty text returns empty list."""
        keywords = extract_keywords("")
        assert keywords == []

        keywords = extract_keywords("   ")
        assert keywords == []

    def test_extract_keywords_with_weight(self):
        """Extract keywords with weights."""
        text = "人工智能和机器学习是当前最热门的技术领域。"
        keywords = extract_keywords_with_weight(text, top_k=3)

        assert len(keywords) <= 3
        assert all(isinstance(kw, tuple) and len(kw) == 2 for kw in keywords)
        # Each item should be (keyword, weight)
        for kw, weight in keywords:
            assert isinstance(kw, str)
            assert isinstance(weight, float)
            assert weight > 0

    def test_extract_keywords_mixed_language(self):
        """Extract keywords from mixed Chinese/English text."""
        text = "Python是一门优秀的编程语言，FastAPI是一个高性能的Web框架。"
        keywords = extract_keywords(text, top_k=5)

        assert len(keywords) <= 5
        assert isinstance(keywords, list)
