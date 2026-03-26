"""
GeeLark XLSX Utilities — Shared helpers for reading/filling GeeLark templates.
"""

import os
import random
from datetime import datetime, timedelta, time as dtime
from typing import Any

# ─── Scheduling: Time Blocks (Direct Paris Hours) ──────────────────
# Single source of truth for all scheduling nodes.
# Hours are PARIS time — written directly to XLSX, no conversion needed.
# GeeLark reads Paris time, so what you see = what GeeLark executes.

TIME_BLOCKS = {
    "☀️ Matin (08h-16h) — Warmup":              {"start_hour": 8,  "end_hour": 16},
    "🌆 Après-midi (16h-22h) — Maintenance":     {"start_hour": 16, "end_hour": 22},
    "🌙 Soir (22h-04h) — Prime Time US":         {"start_hour": 22, "end_hour": 4},
}

TIME_BLOCK_CHOICES = list(TIME_BLOCKS.keys())

# Minimum delay between sequential tasks (warmup). Guard-rail.
MIN_SEQUENTIAL_DELAY = 15  # minutes

# Mapping from BOOLEAN toggle names → TIME_BLOCKS keys
BLOCK_KEYS = {
    "block_matin":     "☀️ Matin (08h-16h) — Warmup",
    "block_apresmidi":  "🌆 Après-midi (16h-22h) — Maintenance",
    "block_soir":      "🌙 Soir (22h-04h) — Prime Time US",
}


def merge_time_blocks(active_keys: list[str]) -> list[dict]:
    """Merge selected TIME_BLOCKS into contiguous ranges.

    Args:
        active_keys: list of TIME_BLOCKS keys that are enabled.

    Returns:
        List of {"start_hour": int, "end_hour": int} dicts, sorted by start_hour.
        Adjacent blocks are fused into a single range.
        E.g. Matin(8-16) + Après-midi(16-22) → [{"start_hour": 8, "end_hour": 22}]
             Matin(8-16) + Soir(22-04)       → [{"start_hour": 8, "end_hour": 16},
                                                  {"start_hour": 22, "end_hour": 4}]

    Raises:
        ValueError: if no blocks are selected.
    """
    if not active_keys:
        raise ValueError("❌ Aucun créneau horaire sélectionné. Coche au moins un bloc.")

    blocks = [TIME_BLOCKS[k] for k in active_keys if k in TIME_BLOCKS]
    if not blocks:
        raise ValueError("❌ Aucun créneau valide trouvé.")

    # Sort by start_hour (put overnight blocks last)
    blocks.sort(key=lambda b: b["start_hour"])

    merged = [dict(blocks[0])]
    for blk in blocks[1:]:
        prev = merged[-1]
        # Adjacent if previous end_hour == current start_hour
        if prev["end_hour"] == blk["start_hour"]:
            prev["end_hour"] = blk["end_hour"]
        else:
            merged.append(dict(blk))

    return merged


def merged_duration_minutes(ranges: list[dict]) -> int:
    """Total duration in minutes across all merged ranges."""
    total = 0
    for r in ranges:
        s, e = r["start_hour"], r["end_hour"]
        total += (24 - s + e if e <= s else e - s) * 60
    return total


def block_duration_minutes(time_block: str) -> int:
    """Calculate the duration of a time block in minutes. Handles overnight blocks."""
    block = TIME_BLOCKS[time_block]
    s, e = block["start_hour"], block["end_hour"]
    return (24 - s + e if e <= s else e - s) * 60



def format_paris_time(dt: datetime) -> str:
    """Format a datetime as 'YYYY-MM-DD HH:MM' for GeeLark XLSX output.
    No timezone conversion — times are already in Paris hours."""
    return dt.strftime("%Y-%m-%d %H:%M")

# Column schemas for each GeeLark template type (1-indexed)
GEELARK_SCHEMAS = {
    "edit_profile": {
        "nickname": 5,
        "username": 6,
        "biography": 7,
        "link_url": 8,
        "link_title": 9,
    },
    "account_warmup": {
        "release_time": 4,
        "number_of_videos": 5,
        "search_keyword": 6,
    },
    "post_reel": {
        "caption": 5,
        "same_url": 6,
        "same_volume": 7,
        "acoustic_volume": 8,
        "ai_tags": 9,
    },
    "reels_gallery": {
        "caption": 5,
        "same_url": 6,
        "ai_tags": 7,
        "publish_post": 8,
    },
}

# Shared columns across all templates
COMMON_COLS = {
    "profile_serial": 1,
    "profile_name": 2,
    "task_no": 3,
    "release_time": 4,
}


def load_template(path: str):
    """Load a GeeLark XLSX template and return (workbook, data_rows)."""
    import openpyxl

    path = path.strip().strip("'\"")
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Template introuvable: '{path}'")
    if not path.lower().endswith(".xlsx"):
        raise ValueError(f"Le template doit être un .xlsx: '{path}'")

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    data_rows = list(ws.iter_rows(min_row=2))
    return wb, data_rows


def fill_column(rows, col_index: int, values: list[str], randomize: bool = True):
    """Fill a specific column across all data rows with values from a pool.
    
    Args:
        rows: openpyxl row objects
        col_index: 1-indexed column number
        values: pool of values to assign
        randomize: shuffle the assignments
    """
    if not values:
        return

    pool = list(values)
    while len(pool) < len(rows):
        pool.extend(values)
    if randomize:
        random.shuffle(pool)
    pool = pool[:len(rows)]

    for row, val in zip(rows, pool):
        if val:
            row[col_index - 1].value = val


def fill_column_single(rows, col_index: int, value: str):
    """Fill a column with the same value for all rows."""
    if not value:
        return
    for row in rows:
        row[col_index - 1].value = value


def save_template(wb, output_path: str) -> str:
    """Save workbook and ensure the output directory exists."""
    output_path = output_path.strip().strip("'\"")
    if not output_path.lower().endswith(".xlsx"):
        output_path += ".xlsx"
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wb.save(output_path)
    return output_path


def get_account_names(rows) -> list[str]:
    """Extract profile names from col 2."""
    return [str(row[1].value) if row[1].value else "unknown" for row in rows]
