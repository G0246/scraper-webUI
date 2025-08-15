# scraper-webUI
# presets.py
# By G0246

from __future__ import annotations

import json
import os
from typing import List, Dict


PRESET_FIELDS = [
    "id",
    "name",
    "url",
    "selector",
    "attribute",
    "user_agent",
    "max_items",
    "next_selector",
    "max_pages",
    "respect_robots",
    "detail_url_selector",
    "detail_url_attribute",
    "detail_image_selector",
    "detail_image_attribute",
]


def _normalize_preset(obj: Dict[str, object]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for field in PRESET_FIELDS:
        value = obj.get(field, "") if isinstance(obj, dict) else ""
        normalized[field] = str(value).strip() if value is not None else ""
    return normalized


def load_presets_any(base_dir: str) -> List[Dict[str, str]]:
    json_path = os.path.join(base_dir, "presets.json")
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            presets = [_normalize_preset(item) for item in data]
            return [p for p in presets if p.get("id") and p.get("name")]
    except Exception:
        return []
    return []


def _presets_path(base_dir: str) -> str:
    return os.path.join(base_dir, "presets.json")


def _write_presets(base_dir: str, presets: List[Dict[str, str]]) -> None:
    path = _presets_path(base_dir)
    tmp_path = path + ".tmp"
    # Ensure directory exists
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)
        f.write("\n")
    # Atomic-ish replace on most platforms
    try:
        os.replace(tmp_path, path)
    except Exception:
        # Fallback
        try:
            os.remove(path)
        except Exception:
            pass
        os.rename(tmp_path, path)


def save_or_update_preset(base_dir: str, preset: Dict[str, str]) -> Dict[str, str]:
    """Save a new preset or update an existing one by id. Returns the normalized preset.

    Required fields: id, name. Other fields will be normalized to strings.
    """
    if not isinstance(preset, dict):
        raise ValueError("preset must be a dict")
    normalized = _normalize_preset(preset)
    pid = (normalized.get("id") or "").strip()
    pname = (normalized.get("name") or "").strip()
    if not pid or not pname:
        raise ValueError("Both 'id' and 'name' are required")

    items = load_presets_any(base_dir)
    updated = False
    for i, it in enumerate(items):
        if it.get("id") == pid:
            items[i] = normalized
            updated = True
            break
    if not updated:
        items.append(normalized)
    _write_presets(base_dir, items)
    return normalized


def delete_preset(base_dir: str, preset_id: str) -> bool:
    preset_id = (preset_id or "").strip()
    if not preset_id:
        raise ValueError("preset_id is required")
    items = load_presets_any(base_dir)
    new_items = [it for it in items if it.get("id") != preset_id]
    if len(new_items) == len(items):
        return False
    _write_presets(base_dir, new_items)
    return True


