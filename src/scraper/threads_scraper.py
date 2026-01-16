from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

import requests

from .utils.error_handler import retry
from .utils.logger import get_logger
from .utils.proxy_manager import ProxyManager

logger = get_logger(__name__)


class ThreadsScraper:
    """Fetch raw Threads items for a username.

    This repo defaults to an offline mode (see config/settings.yaml) so runs are
    deterministic and don't require browser automation.

    Returned items are "raw" dicts that `ThreadsParser` can normalize.
    """

    def __init__(self, settings: Dict[str, Any], config_dir: Path, data_dir: Path):
        self.settings = settings or {}
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)

        self.base_url = str(self.settings.get("base_url") or "https://www.threads.net").rstrip("/")
        self.timeout = int(self.settings.get("timeout") or 15)
        self.use_offline = bool(self.settings.get("use_offline", False))
        self.use_proxies = bool(self.settings.get("use_proxies", False))
        self.limit_default = int(self.settings.get("limit") or 50)

        self.playwright_headless = bool(self.settings.get("playwright_headless", True))
        self.playwright_user_data_dir = (self.settings.get("playwright_user_data_dir") or "").strip() or os.getenv(
            "PLAYWRIGHT_USER_DATA_DIR", ""
        ).strip()

        cookie = (self.settings.get("cookie") or "").strip() or os.getenv("THREADS_COOKIE", "").strip()

        self.raw_dir = self.data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            }
        )
        if cookie:
            self._session.headers["Cookie"] = cookie

        self._proxy_manager: Optional[ProxyManager] = None
        if self.use_proxies:
            self._proxy_manager = ProxyManager(self.raw_dir / "proxies.json")

    def fetch_user_threads(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        username = (username or "").lstrip("@").strip()
        if not username:
            return []

        effective_limit = self.limit_default if limit is None else int(limit)
        effective_limit = max(1, effective_limit)

        if self.use_offline:
            return self._get_offline_threads(username=username, limit=effective_limit)

        return self._get_online_threads(username=username, limit=effective_limit)

    def open_login(self, start_url: Optional[str] = None) -> None:
        """Open a headed persistent browser so the user can login interactively.

        This stores the session in `playwright_user_data_dir` so later runs can scrape
        with the same logged-in context.
        """
        if not self.playwright_user_data_dir:
            raise RuntimeError(
                "Persistent login requires `playwright_user_data_dir` (set it in config/settings.yaml or pass --profile-dir)."
            )
        # Force headed for login.
        self.playwright_headless = False

        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright is required for online mode. Install it with: pip install playwright; then run: playwright install chromium"
            ) from e

        proxy = self._proxy_manager.get_proxy() if self._proxy_manager else None
        pw_proxy = self._to_playwright_proxy(proxy)

        user_data_dir = str(Path(self.playwright_user_data_dir).expanduser().resolve())
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        url = start_url or self.base_url

        logger.info("Opening browser for login...")
        logger.info(f"Profile dir: {user_data_dir}")
        logger.info(f"Navigate/login at: {url}")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                proxy=pw_proxy,
                viewport={"width": 1280, "height": 900},
                user_agent=self._session.headers.get("User-Agent"),
            )
            try:
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                page.wait_for_timeout(1000)
            except Exception:
                # If the user closes the window immediately, just fall through.
                pass

            logger.info("Log in in the opened browser window.")
            logger.info("When you are done, come back here and press Enter to close the browser.")
            try:
                input()
            except KeyboardInterrupt:
                pass
            try:
                context.close()
            except Exception:
                # Already closed by the user.
                pass

    def _offline_path(self, username: str) -> Path:
        safe = "".join(ch for ch in username if ch.isalnum() or ch in ("_", "-"))
        return self.raw_dir / f"offline_{safe}.json"

    def _get_offline_threads(self, username: str, limit: int) -> List[Dict[str, Any]]:
        path = self._offline_path(username)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data[:limit]
            except Exception as e:
                logger.warning(f"Failed to read offline cache {path}: {e}. Regenerating.")

        items = self._generate_offline_items(username=username, limit=limit)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write offline cache {path}: {e}")

        return items

    def _generate_offline_items(self, username: str, limit: int) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        items: List[Dict[str, Any]] = []
        # stable-ish IDs per username and index
        base = abs(hash(username)) % 10_000_000
        for i in range(limit):
            created = (now - timedelta(minutes=7 * i)).isoformat() + "Z"
            item_id = f"{base + i}"  # stringable
            items.append(
                {
                    "id": item_id,
                    "username": username,
                    "text": f"[offline] Sample Threads post #{i + 1} for @{username}",
                    "like_count": int((base + i) % 200),
                    "reply_count": int((base + i * 3) % 50),
                    "repost_count": int((base + i * 5) % 25),
                    "created_at": created,
                    "url": f"{self.base_url}/@{username}",
                }
            )
        return items

    def _get_online_threads(self, username: str, limit: int) -> List[Dict[str, Any]]:
        profile_url = f"{self.base_url}/@{username}"

        # Tuning knobs (optional in settings.yaml)
        max_scrolls = int(self.settings.get("max_scrolls", 20) or 20)
        scroll_pause_ms = int(self.settings.get("scroll_pause_ms", 1200) or 1200)
        settle_ms = int(self.settings.get("page_settle_ms", 2500) or 2500)
        stagnant_limit = int(self.settings.get("stagnant_scrolls", 3) or 3)

        # 1) Fast path: plain HTTP fetch and parse embedded JSON (works when not blocked).
        try:
            html = self._get(profile_url).text
            items = self._extract_items_from_threads_html(html, fallback_url=profile_url)
            if items:
                if len(items) >= limit:
                    return items[:limit]
                # Try to top up via Playwright scrolling.
                pw_items = self._collect_posts_with_playwright(
                    url=profile_url,
                    target_count=limit,
                    max_scrolls=max_scrolls,
                    settle_ms=settle_ms,
                    scroll_pause_ms=scroll_pause_ms,
                )
                if pw_items:
                    merged = self._merge_unique_by_id(items + pw_items, fallback_url=profile_url)
                    return merged[:limit]
                return items[:limit]
        except Exception as e:
            logger.info(f"HTTP parse failed for @{username}: {e}. Falling back to Playwright.")

        # 2) Fallback: Playwright scroll collection.
        items = self._collect_posts_with_playwright(
            url=profile_url,
            target_count=limit,
            max_scrolls=max_scrolls,
            settle_ms=settle_ms,
            scroll_pause_ms=scroll_pause_ms,
            stagnant_limit=stagnant_limit,
        )
        if items:
            return items[:limit]

        raise RuntimeError(
            "Could not extract posts from Threads page. "
            "Threads may be blocking automated access; try setting a valid THREADS_COOKIE in .env, "
            "enable proxies, or switch back to offline mode."
        )

    def _extract_items_from_json_payloads(self, payloads: List[Any], fallback_url: str) -> List[Dict[str, Any]]:
        all_items: List[Dict[str, Any]] = []
        for p in payloads:
            try:
                all_items.extend(self._find_post_like_objects(p))
            except Exception:
                continue
        if not all_items:
            return []

        seen: set[str] = set()
        unique: List[Dict[str, Any]] = []
        for obj in all_items:
            pid = obj.get("id") or obj.get("pk") or obj.get("code")
            key = str(pid) if pid is not None else json.dumps(obj, sort_keys=True, default=str)[:200]
            if key in seen:
                continue
            seen.add(key)
            url = obj.get("url")
            if not url:
                obj = {**obj, "url": fallback_url}
            unique.append(obj)
        return unique

    def _merge_unique_by_id(self, items: List[Dict[str, Any]], fallback_url: str) -> List[Dict[str, Any]]:
        seen: set[str] = set()
        out: List[Dict[str, Any]] = []
        for obj in items:
            pid = obj.get("id") or obj.get("pk") or obj.get("code")
            if pid is None:
                continue
            key = str(pid)
            if key in seen:
                continue
            seen.add(key)
            if not obj.get("url"):
                obj = {**obj, "url": fallback_url}
            out.append(obj)
        return out

    def _extract_items_from_threads_html(self, html: str, fallback_url: str) -> List[Dict[str, Any]]:
        """Best-effort extractor.

        Threads is a Next.js site and often embeds JSON in a script tag. We attempt:
        - <script id="__NEXT_DATA__" type="application/json">{...}</script>
        If found, recursively walk the JSON and pull likely post-shaped objects.
        """

        next_data = self._extract_next_data_json(html)
        if not next_data:
            return []

        candidates = self._find_post_like_objects(next_data)
        if not candidates:
            return []

        # De-duplicate by any stable identifier we can find.
        seen: set[str] = set()
        unique: List[Dict[str, Any]] = []
        for obj in candidates:
            pid = obj.get("id") or obj.get("pk") or obj.get("code")
            key = str(pid) if pid is not None else json.dumps(obj, sort_keys=True, default=str)[:200]
            if key in seen:
                continue
            seen.add(key)
            url = obj.get("url")
            if not url:
                obj = {**obj, "url": fallback_url}
            unique.append(obj)
        return unique

    def _extract_next_data_json(self, html: str) -> Optional[Dict[str, Any]]:
        # Non-greedy capture between script tags.
        m = re.search(
            r"<script[^>]*id=\"__NEXT_DATA__\"[^>]*>(?P<json>\{.*?\})</script>",
            html,
            flags=re.DOTALL,
        )
        if not m:
            return None
        try:
            return json.loads(m.group("json"))
        except Exception:
            return None

    def _find_post_like_objects(self, node: Any) -> List[Dict[str, Any]]:
        """Walk arbitrary JSON and return dicts that look like Threads posts."""
        found: List[Dict[str, Any]] = []

        def is_post_dict(d: Dict[str, Any]) -> bool:
            # Heuristics:
            # - must have an id-ish key
            # - must also have *some* content signal (caption/text) or metadata (timestamp/metrics)
            if not any(k in d for k in ("id", "pk", "code")):
                return False

            text_val = d.get("text")
            if isinstance(text_val, str) and text_val.strip():
                return True

            caption = d.get("caption")
            if isinstance(caption, dict):
                cap_text = caption.get("text")
                if isinstance(cap_text, str) and cap_text.strip():
                    return True
            elif isinstance(caption, str) and caption.strip():
                return True

            has_ts = any(k in d and d.get(k) not in (None, "") for k in ("taken_at", "timestamp", "created_at"))
            has_metrics = any(k in d for k in ("like_count", "likes", "comment_count", "replies", "repost_count", "reposts"))
            return bool(has_ts or has_metrics)

        def walk(x: Any):
            if isinstance(x, dict):
                # common nesting: avoid wrapping the post, return the post dict itself to prevent duplicates
                if "post" in x and isinstance(x.get("post"), dict) and is_post_dict(x["post"]):
                    found.append(x["post"])
                if is_post_dict(x):
                    found.append(x)
                for k, v in x.items():
                    # Don't recursively walk the same post again after adding it.
                    if k == "post" and isinstance(v, dict) and is_post_dict(v):
                        continue
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)

        walk(node)
        return found

    @dataclass(frozen=True)
    class _PlaywrightProxy:
        server: str
        username: Optional[str] = None
        password: Optional[str] = None

        def to_dict(self) -> Dict[str, str]:
            d: Dict[str, str] = {"server": self.server}
            if self.username:
                d["username"] = self.username
            if self.password:
                d["password"] = self.password
            return d

    def _to_playwright_proxy(self, proxy: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        if not proxy:
            return None
        raw = proxy.get("https") or proxy.get("http")
        if not raw:
            return None
        parsed = urlparse(raw)
        if not parsed.scheme or not parsed.hostname:
            return None
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.port else f"{parsed.scheme}://{parsed.hostname}"
        return self._PlaywrightProxy(server=server, username=parsed.username, password=parsed.password).to_dict()

    def _cookie_header_to_cookie_list(self, cookie_header: str) -> List[Dict[str, Any]]:
        cookie_header = (cookie_header or "").strip()
        if not cookie_header:
            return []
        cookies: List[Dict[str, Any]] = []
        # Very basic parse: key=value; key2=value2
        parts = [p.strip() for p in cookie_header.split(";") if p.strip()]
        for part in parts:
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".threads.net",
                    "path": "/",
                }
            )
        return cookies

    def _render_profile_with_playwright(self, url: str) -> tuple[str, List[Any]]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright is required for online mode fallback. Install it with: pip install playwright; "
                "then run: playwright install chromium"
            ) from e

        proxy = self._proxy_manager.get_proxy() if self._proxy_manager else None
        pw_proxy = self._to_playwright_proxy(proxy)

        cookie_header = self._session.headers.get("Cookie", "")
        cookies = self._cookie_header_to_cookie_list(cookie_header)

        json_payloads: List[Any] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=pw_proxy)
            context = browser.new_context(
                user_agent=self._session.headers.get("User-Agent"),
                viewport={"width": 1280, "height": 900},
            )
            if cookies:
                context.add_cookies(cookies)

            page = context.new_page()

            def on_response(resp):
                try:
                    if len(json_payloads) >= 30:
                        return
                    rurl = resp.url or ""
                    if "graphql" not in rurl and "/api/" not in rurl:
                        return
                    if resp.status != 200:
                        return
                    payload = None
                    try:
                        payload = resp.json()
                    except Exception:
                        try:
                            payload = json.loads(resp.text())
                        except Exception:
                            return
                    json_payloads.append(payload)
                except Exception:
                    return

            page.on("response", on_response)

            # networkidle can hang; prefer domcontentloaded with short settling wait
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            page.wait_for_timeout(2500)

            # small scroll to trigger timeline loading (best-effort)
            try:
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(1500)
            except Exception:
                pass

            html = page.content()
            context.close()
            browser.close()
            return html, json_payloads

    def _collect_posts_with_playwright(
        self,
        url: str,
        target_count: int,
        max_scrolls: int,
        settle_ms: int,
        scroll_pause_ms: int,
        stagnant_limit: int,
    ) -> List[Dict[str, Any]]:
        """Collect post-like objects by rendering and scrolling.

        Threads typically loads timeline batches via JSON (often GraphQL). We capture those
        responses and keep scrolling until we have enough unique post ids or the page stops
        producing new items.
        """
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright is required for online mode. Install it with: pip install playwright; "
                "then run: playwright install chromium"
            ) from e

        proxy = self._proxy_manager.get_proxy() if self._proxy_manager else None
        pw_proxy = self._to_playwright_proxy(proxy)

        cookie_header = self._session.headers.get("Cookie", "")
        cookies = self._cookie_header_to_cookie_list(cookie_header)

        posts_by_id: Dict[str, Dict[str, Any]] = {}
        json_payloads: List[Any] = []

        def ingest_payload(payload: Any):
            try:
                for obj in self._find_post_like_objects(payload):
                    pid = obj.get("id") or obj.get("pk") or obj.get("code")
                    if pid is None:
                        continue
                    key = str(pid)
                    if key not in posts_by_id:
                        if not obj.get("url"):
                            obj = {**obj, "url": url}
                        posts_by_id[key] = obj
            except Exception:
                return

        with sync_playwright() as p:
            browser = None
            context = None
            page = None

            # If a user data dir is configured, we use a persistent context.
            # This lets you log in once (with headless=false) and then reuse the session.
            if self.playwright_user_data_dir:
                user_data_dir = str(Path(self.playwright_user_data_dir).expanduser().resolve())
                Path(user_data_dir).mkdir(parents=True, exist_ok=True)
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=self.playwright_headless,
                    proxy=pw_proxy,
                    viewport={"width": 1280, "height": 900},
                    user_agent=self._session.headers.get("User-Agent"),
                )
                if cookies:
                    context.add_cookies(cookies)
                page = context.new_page()
            else:
                browser = p.chromium.launch(headless=self.playwright_headless, proxy=pw_proxy)
                context = browser.new_context(
                    user_agent=self._session.headers.get("User-Agent"),
                    viewport={"width": 1280, "height": 900},
                )
                if cookies:
                    context.add_cookies(cookies)
                page = context.new_page()

            def on_response(resp):
                try:
                    rurl = resp.url or ""
                    if "graphql" not in rurl and "/api/" not in rurl:
                        return
                    if resp.status != 200:
                        return
                    payload = None
                    try:
                        payload = resp.json()
                    except Exception:
                        try:
                            payload = json.loads(resp.text())
                        except Exception:
                            return
                    # keep a few payloads around for debugging/secondary parsing
                    if len(json_payloads) < 120:
                        json_payloads.append(payload)
                    ingest_payload(payload)
                except Exception:
                    return

            page.on("response", on_response)

            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            page.wait_for_timeout(settle_ms)

            last_count = len(posts_by_id)
            stagnant_loops = 0
            try:
                last_height = page.evaluate("document.body.scrollHeight")
            except Exception:
                last_height = None
            stagnant_height = 0

            for _ in range(max_scrolls):
                if len(posts_by_id) >= target_count:
                    break

                try:
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    page.wait_for_timeout(50)
                    page.mouse.wheel(0, 1600)
                except Exception:
                    pass
                page.wait_for_timeout(scroll_pause_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=1500)
                except Exception:
                    pass

                # If the page isn't yielding anything new, stop after a few tries.
                current = len(posts_by_id)
                if current <= last_count:
                    stagnant_loops += 1
                else:
                    stagnant_loops = 0
                    last_count = current
                try:
                    current_height = page.evaluate("document.body.scrollHeight")
                except Exception:
                    current_height = None
                if current_height is not None and last_height is not None:
                    if current_height <= last_height:
                        stagnant_height += 1
                    else:
                        stagnant_height = 0
                        last_height = current_height
                if stagnant_loops >= stagnant_limit and stagnant_height >= stagnant_limit:
                    break

            html = page.content()
            context.close()
            if browser is not None:
                browser.close()

        # If for some reason response capture didn't work, fall back to HTML extraction.
        if posts_by_id:
            return list(posts_by_id.values())

        items = self._extract_items_from_threads_html(html, fallback_url=url)
        if items:
            return items[:target_count]
        items = self._extract_items_from_json_payloads(json_payloads, fallback_url=url)
        return items[:target_count] if items else []

    @retry((requests.RequestException,), tries=3, delay=1.0, backoff=2.0)
    def _get(self, url: str) -> requests.Response:
        proxies = self._proxy_manager.get_proxy() if self._proxy_manager else None
        resp = self._session.get(url, timeout=self.timeout, proxies=proxies)
        resp.raise_for_status()
        # light pacing to avoid tight loops
        time.sleep(0.1)
        return resp
