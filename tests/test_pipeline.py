from pathlib import Path

from podscript_pipeline.pipeline import run_pipeline


def test_run_pipeline(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    res = run_pipeline("t123", "https://example.com/media", str(artifacts))
    assert Path(res["srt_path"]).exists()
    assert Path(res["md_path"]).exists()
    assert res["meta"]["segments"] == 2