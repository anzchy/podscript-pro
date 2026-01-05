from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient

from podscript_api.main import app, TASKS
from podscript_pipeline.pipeline import run_pipeline_from_file
from podscript_shared.models import AppConfig


client = TestClient(app)

# Test user ID and JWT secret for authentication
TEST_USER_ID = "test-user-id-12345"
TEST_JWT_SECRET = "test-jwt-secret-key-for-testing-purposes"


def get_test_auth_cookie():
    """Generate a valid JWT token as cookie for authenticated requests."""
    payload = {
        "sub": TEST_USER_ID,
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return {"access_token": token}


def get_mock_config():
    """Get a mock AppConfig with test JWT secret."""
    return AppConfig(
        supabase_jwt_secret=TEST_JWT_SECRET,
    )


def test_upload_endpoint(tmp_path: Path):
    """Test upload endpoint with authentication."""
    with patch("podscript_api.middleware.auth.load_config", return_value=get_mock_config()):
        cookies = get_test_auth_cookie()
        data = b"\x00\x01\x02"
        files = {"file": ("sample.mp4", data, "video/mp4")}
        r = client.post("/tasks/upload", files=files, cookies=cookies)
        assert r.status_code == 200
        task_id = r.json()["id"]
        assert task_id in TASKS


def test_upload_requires_auth(tmp_path: Path):
    """Test that upload without auth returns 401."""
    data = b"\x00\x01\x02"
    files = {"file": ("sample.mp4", data, "video/mp4")}
    r = client.post("/tasks/upload", files=files)
    assert r.status_code == 401


def test_run_pipeline_from_file(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    src = tmp_path / "sample.mp4"
    src.write_bytes(b"test")
    res = run_pipeline_from_file("t124", str(src), str(artifacts), "video/mp4")
    assert Path(res["srt_path"]).exists()
    assert Path(res["md_path"]).exists()