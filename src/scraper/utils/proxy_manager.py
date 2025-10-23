from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Optional, List
from .logger import get_logger
logger = get_logger(__name__)
class ProxyManager:
    """
    Load a list of proxies from proxies.json and provide them in a round-robin fashion.
    proxies.json format:
      [
        {"http": "http://user:pass@host:port", "https": "http://user:pass@host:port"},
        {"http": "http://host2:port", "https": "http://host2:port"}
      ]
    """
    def __init__(self, proxies_path: Path):
        self.proxies_path = Path(proxies_path)
        self._idx = 0
        self._proxies: List[Dict[str, str]] = self._load()
    def _load(self) -> List[Dict[str, str]]:
        if not self.proxies_path.exists():
            logger.info(f"No proxies.json found at {self.proxies_path}. Proceeding without proxies.")
            return []
        try:
            with open(self.proxies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [p for p in data if isinstance(p, dict)]
            return []
        except Exception as e:
            logger.exception(f"Failed to read proxies.json: {e}")
            return []
    def get_proxy(self) -> Optional[Dict[str, str]]:
        if not self._proxies:
            return None
        prox = self._proxies[self._idx % len(self._proxies)]
        self._idx += 1
        return proxy
