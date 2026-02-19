import os
from pathlib import Path


def get_sqlite_db_path() -> str:
    """Return a stable absolute path for the SQLite database file."""
    from_env = os.getenv("FLIGHTS_DB_PATH")
    if from_env:
        return str(Path(from_env).expanduser().resolve())

    repo_root = Path(__file__).resolve().parent.parent
    return str((repo_root / "flights.db").resolve())

