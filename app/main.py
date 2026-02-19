import asyncio
import os
import sqlite3
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from database import json_to_sqlite
from paths import get_sqlite_db_path
from query_chain import stream_response
from sync_flights import sync_online_flights

# Initialize the FastAPI app
app = FastAPI(title="Flight Query API")

# Allow all origins (you can limit this to specific domains in production)
origins = [
    "http://localhost:3000",  # Add your frontend's URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sync_task = None
SQLITE_DB_PATH = get_sqlite_db_path()


@app.get("/stream")
async def stream_query(question: str = Query(...)):
    return EventSourceResponse(
        stream_response(question),
        media_type="text/event-stream"
    )


async def run_online_sync_loop():
    interval_minutes = int(os.getenv("FLIGHT_SYNC_CHECK_INTERVAL_MINUTES", os.getenv("FLIGHT_SYNC_INTERVAL_MINUTES", "5")))
    while True:
        try:
            stats = await asyncio.to_thread(sync_online_flights, SQLITE_DB_PATH)
            if stats.get("skipped"):
                print(
                    "Online sync skipped (recently updated). "
                    f"Remaining seconds={stats.get('remaining_seconds', 0)}"
                )
            else:
                print(f"Online sync complete. Inserted={stats['inserted']}, Updated={stats['updated']}")
        except Exception as exc:
            print(f"Online sync skipped/failed: {exc}")
        await asyncio.sleep(interval_minutes * 60)


# Event handlers for startup and shutdown
@app.on_event("startup")
async def startup_event():
    global sync_task

    db_path = Path(SQLITE_DB_PATH)
    # Check if database file exists and is empty
    if is_database_empty(db_path):
        json_to_sqlite('./data/flight_data.json', SQLITE_DB_PATH)

    if os.getenv("ENABLE_ONLINE_FLIGHT_SYNC", "false").lower() == "true":
        sync_task = asyncio.create_task(run_online_sync_loop())


@app.on_event("shutdown")
async def shutdown_event():
    if sync_task:
        sync_task.cancel()


def is_database_empty(db_path):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if flights table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flights'")
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            return True

        # If table exists, check number of rows
        cursor.execute("SELECT COUNT(*) FROM flights")
        row_count = cursor.fetchone()[0]

        return row_count == 0

    except sqlite3.Error as e:
        print(f"Error checking database: {e}")
        return True
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
