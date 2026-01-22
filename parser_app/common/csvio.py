import csv
import json
import os
from typing import Any, Dict


def save_csv_row(row: Dict[str, Any], path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    prepared = dict(row)
    if isinstance(prepared.get("images"), (list, tuple)):
        prepared["images"] = json.dumps(prepared.get("images") or [], ensure_ascii=False)
    if isinstance(prepared.get("characteristics"), dict):
        prepared["characteristics"] = json.dumps(prepared.get("characteristics") or {}, ensure_ascii=False)
    if isinstance(prepared.get("metadata"), dict):
        prepared["metadata"] = json.dumps(prepared.get("metadata") or {}, ensure_ascii=False)

    fieldnames = list(prepared.keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(prepared)
