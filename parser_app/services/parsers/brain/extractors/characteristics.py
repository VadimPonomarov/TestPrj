import json
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


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
    selectors: List[Tuple[str, str, str]] = [
        (
            "div.product-characteristic__item",
            "div.product-characteristic__title",
            "div.product-characteristic__value",
        ),
        (
            "div.product-properties__item",
            "div.product-properties__title",
            "div.product-properties__value",
        ),
        (
            "li.characteristics__list-item",
            "span.characteristics__name",
            "span.characteristics__value",
        ),
    ]

    for container_selector, key_selector, value_selector in selectors:
        containers = soup.select(container_selector)
        if not containers:
            continue

        for container in containers:
            key_node = container.select_one(key_selector)
            value_node = container.select_one(value_selector)
            key = key_node.get_text(" ", strip=True) if key_node else None
            value = value_node.get_text(" ", strip=True) if value_node else None
            if key and value:
                characteristics[key] = value

        if characteristics:
            return characteristics

    table = soup.select_one("table.characteristics, table.product-characteristics")
    if table:
        for row in table.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(" ", strip=True)
                value = cells[1].get_text(" ", strip=True)
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
