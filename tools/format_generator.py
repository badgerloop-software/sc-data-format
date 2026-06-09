"""Build format.json content from parsed spreadsheet signals."""

from __future__ import annotations

import json
from typing import Any

from sheet_parser import ParsedSignal, _type_bytes


def _load_existing(path: str) -> dict[str, list[Any]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _entry_from_signal(signal: ParsedSignal, existing: dict[str, list[Any]], config: dict[str, Any]) -> list[Any]:
    if signal.key in existing:
        old = existing[signal.key]
        units = old[2] if old[2] else signal.units
        nmin = old[3] if old[3] != 100 or signal.nominal_min == 0 else signal.nominal_min
        nmax = old[4] if old[4] != 100 or signal.nominal_max == 100 else signal.nominal_max
        category = signal.category or old[5]
    else:
        units = signal.units
        nmin = signal.nominal_min
        nmax = signal.nominal_max
        category = signal.category

    defaults = config.get("signal_defaults", {}).get(signal.key, {})
    data_type = defaults.get("data_type", signal.data_type)
    nbytes = _type_bytes(data_type)
    if signal.key in existing:
        old = existing[signal.key]
        nbytes = old[0]
        data_type = old[1]

    return [
        nbytes,
        data_type,
        units,
        nmin,
        nmax,
        category,
        signal.can_id,
        signal.bit_offset,
    ]


def merge_signals(
    existing_path: str,
    parsed: list[ParsedSignal],
    config: dict[str, Any],
) -> tuple[dict[str, list[Any]], list[ParsedSignal]]:
    existing = _load_existing(existing_path)
    # Update-only merge: start from the committed file and overlay parsed rows.
    merged = dict(existing)

    duplicates: dict[str, ParsedSignal] = {}
    for signal in parsed:
        if signal.key in duplicates:
            signal.warnings.append(
                f"duplicate key also defined on {duplicates[signal.key].sheet} row {duplicates[signal.key].row}"
            )
        duplicates[signal.key] = signal
        merged[signal.key] = _entry_from_signal(signal, existing, config)

    return merged, list(duplicates.values())


def _ordered_keys(merged: dict[str, list[Any]], config: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    bms_keys = sorted(k for k, v in merged.items() if v[5] == "Battery;BMS")
    for key in bms_keys:
        ordered.append(key)
        seen.add(key)

    for section in config.get("section_order", []):
        for key in section.get("keys", []):
            if key in merged and key not in seen:
                ordered.append(key)
                seen.add(key)

    for key in sorted(merged):
        if key not in seen:
            ordered.append(key)

    return ordered


def render_format_json(merged: dict[str, list[Any]], config: dict[str, Any]) -> str:
    keys = _ordered_keys(merged, config)
    lines = ["{"]

    section_tails: set[str] = set()
    for section in config.get("section_order", []):
        section_keys = section.get("keys", [])
        if section_keys:
            section_tails.add(section_keys[-1])

    last_bms = sorted(k for k, v in merged.items() if v[5] == "Battery;BMS")[-1] if any(
        v[5] == "Battery;BMS" for v in merged.values()
    ) else None

    for idx, key in enumerate(keys):
        value = merged[key]
        comma = "," if idx < len(keys) - 1 else ""
        lines.append(f'  "{key}": {json.dumps(value, separators=(", ", ": "))}{comma}')
        if key == last_bms or key in section_tails:
            if idx < len(keys) - 1:
                lines.append("")

    lines.append("}")
    return "\n".join(lines) + "\n"
