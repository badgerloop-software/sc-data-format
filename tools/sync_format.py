#!/usr/bin/env python3
"""Sync format.json from the firmware signal spreadsheet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import yaml

from diff_report import build_report
from drive_download import download_spreadsheet
from format_generator import merge_signals, render_format_json
from sheet_parser import parse_workbook


def _load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(TOOLS_DIR / "config.yaml"))
    parser.add_argument("--format", default=str(REPO_ROOT / "format.json"))
    parser.add_argument("--local-xlsx", help="Use a local spreadsheet instead of Google Drive")
    parser.add_argument("--sheet-file-id", help="Google Drive file ID (or GOOGLE_SHEET_FILE_ID env)")
    parser.add_argument("--download-path", default=str(TOOLS_DIR / "downloads" / "spreadsheet.xlsx"))
    parser.add_argument("--report", default=str(TOOLS_DIR / "reports" / "sync-report.md"))
    parser.add_argument("--dry-run", action="store_true", help="Do not write format.json")
    args = parser.parse_args()

    config = _load_config(Path(args.config))
    format_path = Path(args.format)

    if args.local_xlsx:
        xlsx_path = args.local_xlsx
    else:
        import os

        file_id = args.sheet_file_id or os.environ.get("GOOGLE_SHEET_FILE_ID")
        if not file_id:
            print("error: provide --local-xlsx or --sheet-file-id / GOOGLE_SHEET_FILE_ID", file=sys.stderr)
            return 2
        xlsx_path = download_spreadsheet(file_id, args.download_path)
        print(f"Downloaded spreadsheet to {xlsx_path}")

    before = _load_json(format_path)
    parsed, notes = parse_workbook(xlsx_path, config)
    merged, parsed_signals = merge_signals(str(format_path), parsed, config)
    after_text = render_format_json(merged, config)
    after = json.loads(after_text)

    report = build_report(before, after, parsed_signals, notes)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote report to {report_path}")

    if before == after:
        print("No changes detected.")
        return 0

    if args.dry_run:
        print("Dry run: format.json not written.")
        return 0

    format_path.write_text(after_text, encoding="utf-8")
    print(f"Updated {format_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
