from __future__ import annotations
import json
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from .utils.logger import get_logger
from .utils.proxy_manager import ProxyManager
from .utils.error_handler import retry
logger = get_logger(__name__)
class ThreadsScraper:
    """
    A pragmatic scraper for Meta's Threads.
    By default, it runs in 'offline' mode using a local sample dump to be reliably runnable
    without network or auth. If `use_offline=False` in settings.yaml or passed via CLI, it will
    attempt to fetch public data via HTTP (best-effort, may require valid cookies or may break
    if endpoints change).
    """
    def __init__(self, settings: Dict[str, Any], config_dir: Path, data_dir: Path):
        self.settings = settings
        self.base_url: str = settings.get("base_url", "https://www.threads.net")
        self.timeout: int = int(settings.get("timeout", 15))
        self.use_offline: bool = bool(settings.get("use_offline", True))
        self.user_agents_path = config_dir / "user_agents.txt"
        self.proxies_path = config_dir / "proxies.json"
        self.data_dir = data_dir
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            }
        )
        self._load_user_agents()
        self._apply_random_ua()
        self.proxy_manager = ProxyManager(self.proxies_path)
        if self.settings.get("use_proxies", False):
            prox = self.proxy_manager.get_proxy()
            if prox:
                self.session.proxies.update(prox)
                logger.info(f"Using proxy: {prox}")
        # Optional cookie/auth support if provided via env
        cookie = self.settings.get("cookie") or self._env("THREADS_COOKIE")
        if cookie:
            self.session.headers.update({"Cookie": cookie})
    def _env(self, key: str) -> Optional[str]:
        import os
        return os.getenv(key)
    def _load_user_agents(self):
        try:
            with open(self.user_agents_path, "r", encoding="utf-8") as f:
                self.user_agents = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
            ]
    def _apply_random_ua(self):
        if self.user_agents:
            ua = random.choice(self.user_agents)
            self.session.headers.update({"User-Agent": ua})
    def _offline_items(self) -> List[Dict[str, Any]]:
        sample_path = self.data_dir / "raw" / "threads_dump.json"
        with open(sample_path, "r", encoding="utf-8") as f:
            return json.load(f)
    @retry(exceptions=(requests.RequestException,), tries=3, delay=1.0, backoff=2.0)
    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        logger.debug(f"GET {url} params={params}")
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if resp.status_code >= 400:
            raise requests.RequestException(f"HTTP {resp.status_code} for {url}")
        return resp
    def fetch_user_threads(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return a list of raw thread objects.
        If offline, returns filtered sample items matching the username (or all if not present).
        If online, BEST-EFFORT: fetch user's page and extract embedded JSON if available.
        """
        if self.use_offline:
            items = self._offline_items()
            # Filter by username if present; otherwise, take first `limit`
            filtered = [it for it in items if it.get("username") == username] or items
            return filtered[:limit]
        # Online best-effort scraping (public HTML parse)
        # Warning: endpoints/markup may change; we keep it simple and robust.
        url = f"{self.base_url}/@{username}"
        resp = self._get(url)
        html = resp.text
        # Very rough extraction of embedded JSON if exists
        start_token = "window.__additionalDataLoaded("
        if start_token not in html:
            logger.warning("Could not find embedded data token; returning empty list.")
            return []
        # Extract the first balanced parentheses content quickly (best-effort).
        start_idx = html.find(start_token)
        open_idx = html.find("(", start_idx) + 1
        close_idx = html.find(");", open_idx)
        payload = html[open_idx:close_idx]
        # The payload format is typically: "path", {...json...}
        try:
            comma_idx = payload.find(",")
            json_str = payload[comma_idx + 1 :].strip()
            if json_str.endswith(")"):
                json_str = json_str[:-1]
            data = json.loads(json_str)
        except Exception:
            logger.exception("Failed to parse embedded JSON")
            return []
        # Traverse to find posts — this is highly dependent on the actual structure.
        # We'll defensively search common keys.
        items: List[Dict[str, Any]] = []
        def walk(obj: Any):
            if isinstance(obj, dict):
                if "thread_items" in obj and isinstance(obj["thread_items"], list):
                    for t in obj["thread_items"]:
                        if isinstance(t, dict):
                            items.append(t)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        walk(data)
        time.sleep(random.uniform(0.5, 1.2))  # gentle pacing
        return items[:limit]
