import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from podscript_api.main import app, TASKS
from podscript_shared.history import HistoryManager
from podscript_shared.models import (
    HistoryRecord,
    HistoryStatus,
    MediaType,
    SourceType,
    TaskStatus,
)


client = TestClient(app)


def test_create_and_fetch_task():
    r = client.post("/tasks", json={"source_url": "https://example.com/media"})
    assert r.status_code == 200
    task = r.json()
    task_id = task["id"]

    r2 = client.get(f"/tasks/{task_id}")
    assert r2.status_code == 200


def test_root_and_favicon():
    r = client.get("/")
    assert r.status_code == 200
    assert "/docs" in r.text
    r2 = client.get("/favicon.ico")
    assert r2.status_code == 204


def test_transcribe_not_found():
    r = client.post("/tasks/nonexistent123/transcribe")
    assert r.status_code == 404


def test_transcribe_wrong_status():
    # Create a task and manually set status to test validation
    r = client.post("/tasks", json={"source_url": "https://example.com/media"})
    task = r.json()
    task_id = task["id"]
    # Force status to queued (before download complete)
    TASKS[task_id].status = TaskStatus.queued
    TASKS[task_id].audio_path = None
    # Try to transcribe before downloaded
    r2 = client.post(f"/tasks/{task_id}/transcribe")
    assert r2.status_code == 400


def test_get_results_not_ready():
    r = client.post("/tasks", json={"source_url": "https://example.com/media"})
    task = r.json()
    r2 = client.get(f"/tasks/{task['id']}/results")
    assert r2.status_code == 400


def test_transcribe_no_audio_path():
    # Create task and set downloaded status but no audio path
    r = client.post("/tasks", json={"source_url": "https://example.com/media"})
    task = r.json()
    task_id = task["id"]
    TASKS[task_id].status = TaskStatus.downloaded
    TASKS[task_id].audio_path = None
    r2 = client.post(f"/tasks/{task_id}/transcribe")
    assert r2.status_code == 400


def test_get_task_not_found():
    r = client.get("/tasks/nonexistent999")
    assert r.status_code == 404


def test_get_results_not_found():
    r = client.get("/tasks/nonexistent999/results")
    assert r.status_code == 404


# ============== History API Tests (T013, T014) ==============

class TestHistoryAPI:
    """Tests for history API endpoints."""

    @staticmethod
    def _create_temp_history_with_records():
        """Create a temporary history file with test records."""
        tmpdir = tempfile.mkdtemp()
        history_path = Path(tmpdir) / "history.json"
        manager = HistoryManager(history_path)

        # Add test records
        for i in range(3):
            record = HistoryRecord(
                task_id=f"test{i:08d}ab",
                title=f"Test Task {i}",
                source_url=f"https://example.com/video{i}",
                source_type=SourceType.YOUTUBE,
                media_type=MediaType.VIDEO,
                duration=100 * (i + 1),
                file_size=1000 * (i + 1),
                tags=["test", f"tag{i}"],
                created_at=datetime.now(timezone.utc),
                viewed=i == 0,  # First one is viewed
                status=HistoryStatus.COMPLETED,
            )
            manager.add_record(record)

        return history_path, tmpdir

    def test_get_history_empty(self):
        """GET /history returns empty list when no records exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.get("/history")
                assert r.status_code == 200
                data = r.json()
                assert data["total"] == 0
                assert data["page"] == 1
                assert data["limit"] == 20
                assert data["records"] == []

    def test_get_history_with_records(self):
        """GET /history returns records when they exist."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.get("/history")
                assert r.status_code == 200
                data = r.json()
                assert data["total"] == 3
                assert len(data["records"]) == 3
                # Most recent first (task2)
                assert data["records"][0]["task_id"] == "test00000002ab"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_get_history_pagination(self):
        """GET /history supports pagination."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                # Page 1 with limit 2
                r = client.get("/history?page=1&limit=2")
                assert r.status_code == 200
                data = r.json()
                assert data["total"] == 3
                assert len(data["records"]) == 2
                assert data["page"] == 1
                assert data["limit"] == 2

                # Page 2 with limit 2
                r = client.get("/history?page=2&limit=2")
                assert r.status_code == 200
                data = r.json()
                assert len(data["records"]) == 1
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_get_history_filter_by_status(self):
        """GET /history can filter by status."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.get("/history?status=completed")
                assert r.status_code == 200
                data = r.json()
                assert data["total"] == 3
                # All should be completed
                for record in data["records"]:
                    assert record["status"] == "completed"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_get_history_record_by_id(self):
        """GET /history/{task_id} returns single record."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.get("/history/test00000001ab")
                assert r.status_code == 200
                data = r.json()
                assert data["task_id"] == "test00000001ab"
                assert data["title"] == "Test Task 1"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_get_history_record_not_found(self):
        """GET /history/{task_id} returns 404 for non-existent record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.get("/history/nonexistent12")
                assert r.status_code == 404
                assert "not found" in r.json()["detail"].lower()

    # T024: PATCH /history/{task_id} tests
    def test_patch_history_record_viewed(self):
        """PATCH /history/{task_id} updates viewed status."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.patch(
                    "/history/test00000001ab",
                    json={"viewed": True}
                )
                assert r.status_code == 200
                assert r.json()["success"] is True

                # Verify the update
                r2 = client.get("/history/test00000001ab")
                assert r2.json()["viewed"] is True
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_patch_history_record_tags(self):
        """PATCH /history/{task_id} updates tags."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                new_tags = ["AI", "Machine Learning", "Python"]
                r = client.patch(
                    "/history/test00000001ab",
                    json={"tags": new_tags}
                )
                assert r.status_code == 200

                # Verify the update
                r2 = client.get("/history/test00000001ab")
                assert r2.json()["tags"] == new_tags
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_patch_history_record_not_found(self):
        """PATCH /history/{task_id} returns 404 for non-existent record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.patch(
                    "/history/nonexistent12",
                    json={"viewed": True}
                )
                assert r.status_code == 404

    # T025: DELETE /history/{task_id} tests
    def test_delete_history_record(self):
        """DELETE /history/{task_id} soft deletes a record."""
        history_path, tmpdir = self._create_temp_history_with_records()
        try:
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.delete("/history/test00000001ab")
                assert r.status_code == 200
                assert r.json()["success"] is True

                # Verify the record is soft deleted (status = deleted)
                r2 = client.get("/history/test00000001ab")
                assert r2.json()["status"] == "deleted"

                # Verify it doesn't appear in list
                r3 = client.get("/history")
                task_ids = [rec["task_id"] for rec in r3.json()["records"]]
                assert "test00000001ab" not in task_ids
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_delete_history_record_not_found(self):
        """DELETE /history/{task_id} returns 404 for non-existent record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            with patch("podscript_api.main.get_history_manager") as mock:
                mock.return_value = HistoryManager(history_path)
                r = client.delete("/history/nonexistent12")
                assert r.status_code == 404