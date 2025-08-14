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


