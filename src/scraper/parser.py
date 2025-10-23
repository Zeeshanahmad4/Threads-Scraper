from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from .utils.logger import get_logger
logger = get_logger(__name__)
class ThreadsParser:
    """
    Parse a raw Threads item into a normalized dict.
    Expected output fields:
      - id
      - username
      - text
      - like_count
      - reply_count
      - repost_count
      - created_at (ISO 8601)
      - url
    """
    def parse_item(self, raw: Dict[str, Any], default_username: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            # Two shapes: our offline shape and a best-effort online raw shape
            if "id" in raw and "text" in raw:
                # Offline sample shape
                created_at = raw.get("created_at")
                created_iso = self._coerce_datetime(created_at)
                return {
                    "id": str(raw.get("id")),
                    "username": raw.get("username") or default_username or "",
                    "text": raw.get("text", "").strip(),
                    "like_count": int(raw.get("like_count", 0)),
                    "reply_count": int(raw.get("reply_count", 0)),
                    "repost_count": int(raw.get("repost_count", 0)),
                    "created_at": created_iso,
                    "url": raw.get("url", ""),
                }
            # Online best-effort shape
            # Commonly, we might see nested shapes like: {"post":{"id":...,"caption":{"text":...}}}
            post = raw.get("post") or raw.get("thread") or raw
            pid = post.get("id") or post.get("pk") or post.get("code") or ""
            caption = (
                (post.get("caption") or {}).get("text")
                if isinstance(post.get("caption"), dict)
                else post.get("caption") or ""
            )
            user_obj = post.get("user") or {}
            username = user_obj.get("username") or default_username or ""
            like_count = post.get("like_count") or post.get("likes") or 0
            reply_count = post.get("comment_count") or post.get("replies") or 0
            repost_count = post.get("repost_count") or post.get("reposts") or 0
            ts = post.get("taken_at") or post.get("timestamp") or post.get("created_at")
            created_iso = self._coerce_datetime(ts)
            url = post.get("url") or ""
            return {
                "id": str(pid),
                "username": username,
                "text": (caption or "").strip(),
                "like_count": int(like_count or 0),
                "reply_count": int(reply_count or 0),
                "repost_count": int(repost_count or 0),
                "created_at": created_iso,
                "url": url,
            }
        except Exception as e:
            logger.exception(f"Failed to parse item: {e}")
            return None
    def _coerce_datetime(self, value) -> str:
        """
        Accepts ISO strings or unix seconds and returns ISO8601 UTC string. Fallback to now().
        """
        if value is None or value == "":
            return datetime.utcnow().isoformat() + "Z"
        try:
            if isinstance(value, (int, float)):
                return datetime.utcfromtimestamp(float(value)).isoformat() + "Z"
            # try parse common ISO forms
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone().isoformat()
        except Exception:
            return datetime.utcnow().isoformat() + "Z"
