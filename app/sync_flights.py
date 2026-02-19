import json
import os
from datetime import date, timedelta
from typing import Dict, List, Tuple

from database import upsert_flights
from providers.amadeus import fetch_flights


def _default_routes() -> List[Tuple[str, str]]:
    return [
        ("New Delhi", "Hanoi"),
        ("New Delhi", "Ho Chi Minh City"),
        ("Mumbai", "Hanoi"),
        ("Mumbai", "Ho Chi Minh City"),
        ("Hanoi", "New Delhi"),
        ("Ho Chi Minh City", "Mumbai"),
    ]


def _load_routes() -> List[Tuple[str, str]]:
    env_routes = os.getenv("FLIGHT_SYNC_ROUTES")
    if not env_routes:
        return _default_routes()

    parsed = json.loads(env_routes)
    routes: List[Tuple[str, str]] = []
    for item in parsed:
        routes.append((item["origin"], item["destination"]))
    return routes


def sync_online_flights(sqlite_file: str = "./flights.db") -> Dict[str, int]:
    routes = _load_routes()
    days_ahead = int(os.getenv("FLIGHT_SYNC_DAYS_AHEAD", "21"))
    max_per_day = int(os.getenv("FLIGHT_SYNC_MAX_PER_DAY", "8"))

    start = date.today()
    end = start + timedelta(days=days_ahead)

    all_rows = []
    for origin, destination in routes:
        rows = fetch_flights(
            origin=origin,
            destination=destination,
            start_date=start,
            end_date=end,
            max_per_day=max_per_day,
        )
        all_rows.extend(rows)

    return upsert_flights(all_rows, sqlite_file)
