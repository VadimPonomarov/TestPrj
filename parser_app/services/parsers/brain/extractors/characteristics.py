import json
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from lxml import etree

from parser_app.common.constants import (
    CHARACTERISTICS_KEY_REL_XPATH,
    CHARACTERISTICS_ROWS_XPATH,
    CHARACTERISTICS_VALUE_REL_XPATH,
)


def extract_characteristics(soup: Optional[BeautifulSoup]) -> Dict[str, Any]:
    if not soup:
        return {}

    characteristic_extractors = [
        lambda: _extract_characteristics_from_dom(soup),
        lambda: _extract_characteristics_from_scripts(soup),
    ]

    for extractor in characteristic_extractors:
        result = extractor()
        if result:
            return result

    return {}


def _extract_characteristics_from_dom(soup: BeautifulSoup) -> Dict[str, Any]:
    characteristics: Dict[str, Any] = {}

    html = str(soup)
    tree = etree.HTML(html) if html else None
    if tree is None:
        return {}

    def _norm(text: str) -> str:
        return " ".join((text or "").split())

    try:
        rows = tree.xpath(CHARACTERISTICS_ROWS_XPATH)
    except Exception:
        rows = []

    for row in rows:
        try:
            key_nodes = row.xpath(CHARACTERISTICS_KEY_REL_XPATH)
            value_nodes = row.xpath(CHARACTERISTICS_VALUE_REL_XPATH)
        except Exception:
            continue

        key = None
        if key_nodes:
            try:
                key = _norm(" ".join(key_nodes[0].itertext()))
            except Exception:
                key = None

        value = None
        if value_nodes:
            try:
                value = _norm(" ".join(value_nodes[0].itertext()))
            except Exception:
                value = None

        if key and value:
            characteristics[key] = value

    if characteristics:
        return characteristics

    try:
        table_rows = tree.xpath(
            "//table[contains(@class,'characteristics') or contains(@class,'product-characteristics')]//tr"
        )
    except Exception:
        table_rows = []

    for row in table_rows:
        try:
            cells = row.xpath("./th|./td")
        except Exception:
            continue
        if len(cells) < 2:
            continue
        try:
            key = _norm(" ".join(cells[0].itertext()))
            value = _norm(" ".join(cells[1].itertext()))
        except Exception:
            continue
        if key and value:
            characteristics[key] = value

    return characteristics


def _extract_characteristics_from_scripts(soup: BeautifulSoup) -> Dict[str, Any]:
    script_nodes = soup.find_all("script")
    for script in script_nodes:
        script_text = script.string or script.get_text(strip=True)
        if not script_text or "character" not in script_text.lower():
            continue

        json_payload = _extract_json_from_script(script_text)
        if not json_payload:
            continue

        if isinstance(json_payload, dict):
            possible = _search_for_characteristics(json_payload)
            if possible:
                return possible

        if isinstance(json_payload, list):
            for item in json_payload:
                if isinstance(item, dict):
                    possible = _search_for_characteristics(item)
                    if possible:
                        return possible

    return {}


def _extract_json_from_script(script_text: str) -> Optional[Any]:
    match = re.search(r"=\s*(\{.*\})\s*;?$", script_text, re.DOTALL)
    if not match:
        match = re.search(r"(\{.*\})", script_text, re.DOTALL)
    if not match:
        return None

    candidate = match.group(1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _search_for_characteristics(payload: Dict[str, Any]) -> Dict[str, Any]:
    candidates: List[Any] = [payload]
    seen: set[int] = set()

    while candidates:
        node = candidates.pop()
        if isinstance(node, dict):
            node_id = id(node)
            if node_id in seen:
                continue
            seen.add(node_id)

            keys_lower = {str(k).lower() for k in node.keys()}
            if any("character" in key for key in keys_lower):
                for key, value in node.items():
                    if isinstance(value, list) and all(isinstance(elem, dict) for elem in value):
                        mapped = _list_of_dicts_to_mapping(value)
                        if mapped:
                            return mapped

            candidates.extend(node.values())
        elif isinstance(node, list):
            candidates.extend(node)

    return {}


def _list_of_dicts_to_mapping(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    for item in items:
        key = item.get("name") or item.get("title") or item.get("label")
        value = item.get("value") or item.get("text")
        if key and value:
            mapping[str(key)] = value
    return mapping


def extract_display_info(characteristics: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    diagonal = None
    resolution = None

    diagonal_keys = [
        "Діагональ екрана",
        "Діагональ",
        "Діагональ екрану",
        "Диагональ экрана",
    ]
    resolution_keys = [
        "Роздільна здатність екрана",
        "Роздільна здатність",
        "Разрешение экрана",
        "Разрешение",
    ]

    for key in diagonal_keys:
        if key in characteristics:
            match = re.search(r"(\d+[\.,]?\d*)", characteristics[key])
            if match:
                diagonal = match.group(1).replace(",", ".")
                break

    for key in resolution_keys:
        if key in characteristics:
            match = re.search(r"(\d+\s*[xх×]\s*\d+)", characteristics[key], re.IGNORECASE)
            if match:
                resolution = (
                    re.sub(r"\s+", "", match.group(1))
                    .lower()
                    .replace("х", "x")
                    .replace("×", "x")
                )
                break

    return diagonal, resolution
