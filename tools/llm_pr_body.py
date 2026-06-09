"""Optional Gemini-generated PR description from sync diff report."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def generate_pr_body(report_path: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _fallback_body(report_path)

    report = open(report_path, encoding="utf-8").read()
    prompt = (
        "Write a concise GitHub pull request description in markdown for a telemetry "
        "format.json sync from the firmware signal spreadsheet. Summarize added, removed, "
        "and changed signals. Call out anything flagged for review. Include a short test plan.\n\n"
        f"Report:\n{report}"
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    import json

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip() + "\n"
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError):
        return _fallback_body(report_path)


def _fallback_body(report_path: str) -> str:
    report = open(report_path, encoding="utf-8").read()
    return (
        "## Summary\n"
        "Automated sync of `format.json` from the firmware signal spreadsheet.\n\n"
        "## Diff report\n"
        f"{report}\n"
    )


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tools/reports/sync-report.md"
    print(generate_pr_body(path))
