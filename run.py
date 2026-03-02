#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
import tempfile
from pathlib import Path

import sys

from market_report.cli import main as cli_main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run market report pipeline with a generic config.")
    parser.add_argument(
        "--config",
        default="configs/projects/consolidado_drive.json",
        help="Path to base project config JSON",
    )
    parser.add_argument(
        "--default-config",
        default="configs/projects/default.json",
        help="Path to default config JSON",
    )
    parser.add_argument("--project", default=None, help="Project name (e.g., Guadalajara)")
    parser.add_argument("--run-id", default=None, help="Optional run identifier")
    return parser.parse_args()


def _resolve_config(base_config_path: str, project: str | None) -> Path:
    base_path = Path(base_config_path)
    data = json.loads(base_path.read_text(encoding="utf-8"))

    if project:
        data["project_name"] = project
        drive_cfg = data.get("google_drive_folder", {})
        subfolder = drive_cfg.get("subfolder_name")
        if isinstance(subfolder, str):
            drive_cfg["subfolder_name"] = subfolder.replace("{PROYECTO}", project)
        data["google_drive_folder"] = drive_cfg

        output_cfg = data.get("output", {})
        filename = output_cfg.get("filename")
        if isinstance(filename, str):
            output_cfg["filename"] = filename.replace("{PROYECTO}", project)
        data["output"] = output_cfg

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    resolved_dir = Path(tempfile.mkdtemp(prefix="market_report_configs_"))
    resolved_path = resolved_dir / f"config_{run_id}.json"
    resolved_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved_path


def main() -> None:
    args = parse_args()

    # Set environment
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = f"{os.getcwd()}/credentials.json"
    os.environ["PYTHONPATH"] = f"{os.getcwd()}/src"

    resolved_config = _resolve_config(args.config, args.project)

    # Delegate to CLI with resolved config
    sys.argv = [
        sys.argv[0],
        "--config",
        str(resolved_config),
        "--default-config",
        args.default_config,
    ]
    if args.run_id:
        sys.argv.extend(["--run-id", args.run_id])
    cli_main()


if __name__ == "__main__":
    main()
