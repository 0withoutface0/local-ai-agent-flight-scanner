import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import REAL, Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Define the Database Model (Table Structure)
Base = declarative_base()

SYNC_KEY_LAST_SUCCESS_EPOCH = "last_successful_online_sync_epoch"


class Flight(Base):
    __tablename__ = 'flights'

    uuid = Column(String, primary_key=True)
    airline = Column(String)
    date = Column(String)
    duration = Column(String)
    flightType = Column(String)
    price = Column(Integer)
    origin = Column(String)
    destination = Column(String)
    originCountry = Column(String)
    destinationCountry = Column(String)
    link = Column(String)
    rainProbability = Column(REAL)
    freeMeal = Column(Integer)


def _coerce_flight(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uuid": item["uuid"],
        "airline": item.get("airline"),
        "date": item.get("date"),
        "duration": item.get("duration"),
        "flightType": item.get("flightType"),
        "price": int(item["price"]) if item.get("price") is not None else None,
        "origin": item.get("origin"),
        "destination": item.get("destination"),
        "originCountry": item.get("originCountry"),
        "destinationCountry": item.get("destinationCountry"),
        "link": item.get("link"),
        "rainProbability": float(item["rainProbability"]) if item.get("rainProbability") is not None else None,
        "freeMeal": int(bool(item.get("freeMeal"))) if item.get("freeMeal") is not None else None,
    }


def _ensure_sync_metadata_table(sqlite_file: str) -> None:
    conn = sqlite3.connect(sqlite_file)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_sync_metadata(key: str, sqlite_file: str) -> Optional[str]:
    _ensure_sync_metadata_table(sqlite_file)
    conn = sqlite3.connect(sqlite_file)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM sync_metadata WHERE key=?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_sync_metadata(key: str, value: str, sqlite_file: str) -> None:
    _ensure_sync_metadata_table(sqlite_file)
    conn = sqlite3.connect(sqlite_file)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sync_metadata(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (key, value, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


def get_flight_count(sqlite_file: str) -> int:
    conn = sqlite3.connect(sqlite_file)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flights'")
        table_exists = cursor.fetchone() is not None
        if not table_exists:
            return 0

        cursor.execute("SELECT COUNT(*) FROM flights")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def upsert_flights(flights: Iterable[Dict[str, Any]], sqlite_file: str) -> Dict[str, int]:
    """Insert or update flights by uuid."""
    engine = create_engine(f"sqlite:///{sqlite_file}")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    inserted = 0
    updated = 0

    try:
        for raw_item in flights:
            item = _coerce_flight(raw_item)
            existing = session.query(Flight).filter_by(uuid=item['uuid']).first()
            if existing:
                for key, value in item.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                session.add(Flight(**item))
                inserted += 1

        session.commit()
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"A database error occurred: {e}") from e
    finally:
        session.close()

    return {"inserted": inserted, "updated": updated}


def json_to_sqlite(json_file: str, sqlite_file: str) -> Dict[str, int]:
    """
    Reads flight data from JSON and inserts/updates it into SQLite database.
    """
    if not Path(json_file).exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    with open(json_file, 'r', encoding='utf-8') as file:
        data: List[Dict[str, Any]] = json.load(file)

    stats = upsert_flights(data, sqlite_file)
    print(
        f"Database operation complete. Inserted {stats['inserted']} new records, "
        f"updated {stats['updated']} existing records."
    )
    return stats
