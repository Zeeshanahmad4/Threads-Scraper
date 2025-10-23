from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from .utils.logger import get_logger
logger = get_logger(__name__)
class Exporter:
    def __init__(self, output_dir: Path, data_dir: Path):
        self.output_dir = Path(output_dir)
        self.data_dir = Path(data_dir)
    def _resolve_path(self, filename: str, subdir: Optional[str] = None) -> Path:
        base = self.output_dir if subdir is None else (self.data_dir / subdir.split("/", 1)[-1])
        base.mkdir(parents=True, exist_ok=True)
        return base / filename
    def to_json(self, items: List[Dict[str, Any]], filename: str = "threads_results.json", subdir: Optional[str] = None) -> Path:
        path = self._resolve_path(filename, subdir=subdir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return path
    def to_csv(self, items: List[Dict[str, Any]], filename: str = "threads_results.csv", subdir: Optional[str] = None) -> Path:
        path = self._resolve_path(filename, subdir=subdir)
        df = pd.DataFrame(items)
        # Ensure consistent column order
        cols = ["id", "username", "text", "like_count", "reply_count", "repost_count", "created_at", "url"]
        for c in cols:
            if c not in df.columns:
                df[c] = None
        df = df[cols]
        df.to_csv(path, index=False)
        return path
