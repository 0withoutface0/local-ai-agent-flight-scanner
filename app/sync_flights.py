import json
import os
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

from database import (
    SYNC_KEY_LAST_SUCCESS_EPOCH,
    get_sync_metadata,
    set_sync_metadata,
    upsert_flights,
)
from paths import get_sqlite_db_path
from providers.amadeus import fetch_flights


def _default_routes() -> List[Tuple[str, str]]:
    return [
        ("Osaka", "Budapest"),
        ("Tokio", "Budapest"),
    ]


def _load_routes() -> List[Tuple[str, str]]:
    env_routes = os.getenv("FLIGHT_SYNC_ROUTES")
    if not env_routes:
        print("no roots")
        return _default_routes()

    parsed = json.loads(env_routes)
    routes: List[Tuple[str, str]] = []
    for item in parsed:
        routes.append((item["origin"], item["destination"]))
    return routes


def _get_last_success_epoch(sqlite_file: str) -> int:
    raw = get_sync_metadata(SYNC_KEY_LAST_SUCCESS_EPOCH, sqlite_file)
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def sync_online_flights(sqlite_file: str | None = None) -> Dict[str, Any]:
    sqlite_file = sqlite_file or get_sqlite_db_path()
    min_gap_minutes = int(os.getenv("FLIGHT_SYNC_MIN_UPDATE_GAP_MINUTES", "10"))
    min_gap_seconds = max(min_gap_minutes, 0) * 60

    now_epoch = int(time.time())
    last_success_epoch = _get_last_success_epoch(sqlite_file)

    if last_success_epoch > 0 and (now_epoch - last_success_epoch) < min_gap_seconds:
        remaining_seconds = min_gap_seconds - (now_epoch - last_success_epoch)
        return {
            "inserted": 0,
            "updated": 0,
            "skipped": True,
            "reason": "minimum_gap_not_elapsed",
            "last_success_epoch": last_success_epoch,
            "remaining_seconds": remaining_seconds,
        }

    routes = _load_routes()
    print("loaded routes")
    days_ahead = int(os.getenv("FLIGHT_SYNC_DAYS_AHEAD", "21"))
    max_per_day = int(os.getenv("FLIGHT_SYNC_MAX_PER_DAY", "8"))

    start = date(2026, 8, 8)
    end = start + timedelta(days=days_ahead)

    all_rows = []
    print("fetching flights")
    for origin, destination in routes:
        rows = fetch_flights(
            origin=origin,
            destination=destination,
            start_date=start,
            end_date=end,
            max_per_day=max_per_day,
        )
        all_rows.extend(rows)
    print("fetched flights")

    stats = upsert_flights(all_rows, sqlite_file)
    set_sync_metadata(SYNC_KEY_LAST_SUCCESS_EPOCH, str(int(time.time())), sqlite_file)
    stats.update({
        "skipped": False,
        "last_success_epoch": int(time.time()),
        "remaining_seconds": 0,
    })
    return stats
