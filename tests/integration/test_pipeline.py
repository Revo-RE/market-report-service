from pathlib import Path

from market_report.application.pipeline import build_default_pipeline


def test_pipeline_runs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = Path(__file__).parents[2] / "configs" / "projects" / "el_cabo.json"
    default_path = Path(__file__).parents[2] / "configs" / "projects" / "default.json"

    pipeline = build_default_pipeline(str(config_path))
    result = pipeline.run(str(config_path), str(default_path), run_id="test_run")

    assert result.ppt_path.exists()
    assert (result.output_dir / "charts").exists()
