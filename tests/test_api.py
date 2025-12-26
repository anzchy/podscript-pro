import time
from fastapi.testclient import TestClient

from podscript_api.main import app, TASKS
from podscript_shared.models import TaskStatus


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