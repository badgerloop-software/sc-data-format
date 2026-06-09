"""Generate a human-readable diff report for format.json sync."""

from __future__ import annotations

import json
from typing import Any

from sheet_parser import ParsedSignal


def _fmt_entry(entry: list[Any]) -> str:
    return json.dumps(entry, separators=(", ", ": "))


def build_report(
    before: dict[str, list[Any]],
    after: dict[str, list[Any]],
    parsed: list[ParsedSignal],
    notes: list[str],
) -> str:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    common = sorted(set(before) & set(after))

    changed: list[tuple[str, list[Any], list[Any]]] = []
    for key in common:
        if before[key] != after[key]:
            changed.append((key, before[key], after[key]))

    flagged = [s for s in parsed if s.warnings]

    lines = ["# format.json sync report", ""]
    lines.append(f"- Signals before: **{len(before)}**")
    lines.append(f"- Signals after: **{len(after)}**")
    lines.append(f"- Added: **{len(added)}** | Removed: **{len(removed)}** | Changed: **{len(changed)}**")
    lines.append("")

    if added:
        lines.append("## Added signals")
        for key in added:
            lines.append(f"- `{key}`: {_fmt_entry(after[key])}")
        lines.append("")

    if removed:
        lines.append("## Removed signals")
        for key in removed:
            lines.append(f"- `{key}`: {_fmt_entry(before[key])}")
        lines.append("")

    if changed:
        lines.append("## Changed signals")
        for key, old, new in changed:
            lines.append(f"- `{key}`")
            lines.append(f"  - before: {_fmt_entry(old)}")
            lines.append(f"  - after: {_fmt_entry(new)}")
        lines.append("")

    if flagged:
        lines.append("## Flagged rows (needs review)")
        for signal in flagged:
            lines.append(
                f"- `{signal.key}` ({signal.sheet} row {signal.row}): {', '.join(signal.warnings)}"
            )
        lines.append("")

    if notes:
        lines.append("## Parser notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
