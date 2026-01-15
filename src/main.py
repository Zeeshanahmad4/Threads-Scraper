import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import yaml
from dotenv import load_dotenv
# Local imports
from scraper.threads_scraper import ThreadsScraper
from scraper.parser import ThreadsParser
from scraper.exporter import Exporter
from scraper.utils.logger import get_logger
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
CONFIG_DIR = ROOT / "config"
logger = get_logger(__name__)
def load_settings(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    return settings
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)
def parse_args(default_usernames: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Threads Scraper — scrape Threads posts for given usernames."
    )
    parser.add_argument(
        "-u",
        "--usernames",
        nargs="+",
        help="Threads usernames to scrape (without @). Defaults to settings.yaml",
        default=default_usernames,
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force offline mode (use local sample dump).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of threads per user to collect (if supported by endpoint).",
    )

    parser.add_argument(
        "--login",
        action="store_true",
        help="Open a real browser to login and save a persistent session (requires profile dir).",
    )
    parser.add_argument(
        "--profile-dir",
        type=str,
        default=None,
        help="Path to persistent Playwright profile directory (defaults to data/playwright-profile).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Playwright with a visible browser window (useful for debugging).",
    )

    parser.add_argument(
        "--keep-empty",
        action="store_true",
        help="Keep items with empty text/caption (media-only posts or non-post objects).",
    )
    return parser.parse_args()
def main():
    load_dotenv()  # load .env if present
    ensure_dirs()
    settings_path = CONFIG_DIR / "settings.yaml"
    settings = load_settings(settings_path)
    args = parse_args(settings.get("usernames", []))
    if not args.usernames:
        logger.error("No usernames provided via CLI or settings.yaml")
        sys.exit(1)
    # Merge CLI overrides into settings
    settings["use_offline"] = args.offline or settings.get("use_offline", False)
    settings["limit"] = args.limit

    # Playwright session/profile options
    if args.profile_dir:
        settings["playwright_user_data_dir"] = args.profile_dir
    if args.headed:
        settings["playwright_headless"] = False

    # Dedicated login flow: open browser, let user login, then exit.
    if args.login:
        settings.setdefault("playwright_user_data_dir", str(DATA_DIR / "playwright-profile"))
        settings["playwright_headless"] = False
        scraper = ThreadsScraper(
            settings=settings,
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
        )
        scraper.open_login()
        logger.info("Login flow complete. Re-run without --login to scrape using the saved session.")
        return
    scraper = ThreadsScraper(
        settings=settings,
        config_dir=CONFIG_DIR,
        data_dir=DATA_DIR,
    )
    parser = ThreadsParser()
    exporter = Exporter(output_dir=OUTPUT_DIR, data_dir=DATA_DIR)
    all_results: List[Dict[str, Any]] = []
    for username in args.usernames:
        try:
            logger.info(f"Collecting threads for @{username} (offline={settings['use_offline']})")
            raw_items = scraper.fetch_user_threads(username=username, limit=settings["limit"])
            parsed_items = [parser.parse_item(item, default_username=username) for item in raw_items]
            parsed_items = [p for p in parsed_items if p]  # drop None
            if not args.keep_empty:
                parsed_items = [p for p in parsed_items if (p.get("text") or "").strip()]
            all_results.extend(parsed_items)
        except Exception as e:
            logger.exception(f"Failed to collect for @{username}: {e}")
    if not all_results:
        logger.warning("No results collected. Exiting.")
        sys.exit(0)
    # Export to /output
    json_path = exporter.to_json(all_results, filename="threads_results.json")
    csv_path = exporter.to_csv(all_results, filename="threads_results.csv")
    # Also create a processed/clean_threads.csv for convenience
    processed_path = exporter.to_csv(all_results, filename="clean_threads.csv", subdir="data/processed")
    logger.info(f"Wrote JSON -> {json_path}")
    logger.info(f"Wrote CSV  -> {csv_path}")
    logger.info(f"Wrote processed CSV -> {processed_path}")
    # Print a short completion message with summary stats
    users = sorted({r["username"] for r in all_results})
    logger.info(
        json.dumps(
            {"users": users, "total_items": len(all_results), "output_json": str(json_path), "output_csv": str(csv_path)},
            indent=2,
        )
    )
if __name__ == "__main__":
    main()
