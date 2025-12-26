from pathlib import Path
from fastapi.testclient import TestClient

from podscript_api.main import app, TASKS
from podscript_pipeline.pipeline import run_pipeline_from_file


client = TestClient(app)


def test_upload_endpoint(tmp_path: Path):
    data = b"\x00\x01\x02"
    files = {"file": ("sample.mp4", data, "video/mp4")}
    r = client.post("/tasks/upload", files=files)
    assert r.status_code == 200
    task_id = r.json()["id"]
    assert task_id in TASKS


def test_run_pipeline_from_file(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    src = tmp_path / "sample.mp4"
    src.write_bytes(b"test")
    res = run_pipeline_from_file("t124", str(src), str(artifacts), "video/mp4")
    assert Path(res["srt_path"]).exists()
    assert Path(res["md_path"]).exists()