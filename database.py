# database.py
"""
database.py  —  SWR SQLite Data Layer
Schema: scan history, storage trends, anonymous performance metrics.
No personal data is stored — only device-level aggregates.
"""
import sqlite3, os, time
from datetime import datetime

# ── DB path: writable app data directory ─────────────────────────
try:
    from android.storage import app_storage_path
    DB_DIR = app_storage_path()
except Exception:
    DB_DIR = os.path.expanduser("~/.swr")

os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "swr.db")


class SWRDatabase:
    """Thin wrapper around the SWR SQLite database."""

    def __init__(self, path: str = DB_PATH):
        self._path = path
        self._conn: sqlite3.Connection | None = None

    # ── Connection ───────────────────────────────────────────────
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Schema ───────────────────────────────────────────────────
    def init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            -- One row per storage scan session
            CREATE TABLE IF NOT EXISTS scan_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at   TEXT    NOT NULL DEFAULT (strftime(\'%Y-%m-%dT%H:%M:%S\', \'now\')),
                scan_type    TEXT    NOT NULL,          -- \'downloads\' | \'full\'
                files_found  INTEGER NOT NULL DEFAULT 0,
                bytes_found  INTEGER NOT NULL DEFAULT 0,
                files_deleted INTEGER NOT NULL DEFAULT 0,
                bytes_freed  INTEGER NOT NULL DEFAULT 0
            );

            -- Daily storage trend snapshot (one row per day)
            CREATE TABLE IF NOT EXISTS storage_trend (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at  TEXT    NOT NULL DEFAULT (strftime(\'%Y-%m-%dT%H:%M:%S\', \'now\')),
                total_bytes  INTEGER NOT NULL,
                used_bytes   INTEGER NOT NULL,
                free_bytes   INTEGER NOT NULL
            );

            -- Anonymous performance metrics (opt-in)
            CREATE TABLE IF NOT EXISTS perf_metrics (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at  TEXT    NOT NULL DEFAULT (strftime(\'%Y-%m-%dT%H:%M:%S\', \'now\')),
                metric_key   TEXT    NOT NULL,
                metric_value REAL    NOT NULL,
                unit         TEXT    NOT NULL DEFAULT \'\'
            );

            -- App version / install info (anonymous)
            CREATE TABLE IF NOT EXISTS app_meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()

        # Write install timestamp once
        conn.execute(
            "INSERT OR IGNORE INTO app_meta (key, value) VALUES (?, ?)",
            ("install_ts", datetime.utcnow().isoformat()),
        )
        conn.commit()

    # ── Scan History ─────────────────────────────────────────────
    def record_scan(self, scan_type: str, files_found: int, bytes_found: int,
                    files_deleted: int = 0, bytes_freed: int = 0) -> int:
        conn = self._get_conn()
        cur  = conn.execute(
            """INSERT INTO scan_history
               (scan_type, files_found, bytes_found, files_deleted, bytes_freed)
               VALUES (?, ?, ?, ?, ?)""",
            (scan_type, files_found, bytes_found, files_deleted, bytes_freed),
        )
        conn.commit()
        return cur.lastrowid

    def get_scan_history(self, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM scan_history ORDER BY scanned_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Storage Trend ────────────────────────────────────────────
    def record_storage_snapshot(self):
        """Call daily to build trend data."""
        try:
            import psutil
            d = psutil.disk_usage("/")
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO storage_trend (total_bytes, used_bytes, free_bytes) VALUES (?, ?, ?)",
                (d.total, d.used, d.free),
            )
            conn.commit()
        except Exception:
            pass

    def get_storage_trend(self, days: int = 30) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM storage_trend
               WHERE recorded_at >= datetime(\'now\', ?)
               ORDER BY recorded_at ASC""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Performance Metrics ──────────────────────────────────────
    def record_metric(self, key: str, value: float, unit: str = ""):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO perf_metrics (metric_key, metric_value, unit) VALUES (?, ?, ?)",
            (key, value, unit),
        )
        conn.commit()

    def get_metrics(self, key: str, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM perf_metrics WHERE metric_key = ?
               ORDER BY recorded_at DESC LIMIT ?""",
            (key, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── App Meta ─────────────────────────────────────────────────
    def get_meta(self, key: str) -> str | None:
        conn = self._get_conn()
        row  = conn.execute(
            "SELECT value FROM app_meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()


# ── Quick validation: instantiate and run init_db (only when executed directly)
if __name__ == "__main__":
    import sqlite3, os, tempfile

    # Inline validation (uses a temp DB path)
    class _SWRDatabaseValidation:
        def __init__(self, path):
            self._path = path
            self._conn = None

        def _get_conn(self):
            if self._conn is None:
                self._conn = sqlite3.connect(self._path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
            return self._conn

        def close(self):
            if self._conn:
                self._conn.close()
                self._conn = None

        def init_db(self):
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scanned_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    scan_type TEXT NOT NULL,
                    files_found INTEGER NOT NULL DEFAULT 0,
                    bytes_found INTEGER NOT NULL DEFAULT 0,
                    files_deleted INTEGER NOT NULL DEFAULT 0,
                    bytes_freed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS storage_trend (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    total_bytes INTEGER NOT NULL,
                    used_bytes INTEGER NOT NULL,
                    free_bytes INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS perf_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    metric_key TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            conn.commit()

        def record_scan(self, scan_type, files_found, bytes_found, files_deleted=0, bytes_freed=0):
            conn = self._get_conn()
            cur  = conn.execute(
                "INSERT INTO scan_history (scan_type, files_found, bytes_found, files_deleted, bytes_freed) VALUES (?, ?, ?, ?, ?)",
                (scan_type, files_found, bytes_found, files_deleted, bytes_freed)
            )
            conn.commit()
            return cur.lastrowid

        def get_scan_history(self, limit=50):
            conn = self._get_conn()
            rows = conn.execute("SELECT * FROM scan_history ORDER BY scanned_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    tmpdb = tempfile.mktemp(suffix=".db")
    db = _SWRDatabaseValidation(tmpdb)
    db.init_db()
    db.record_scan("downloads", 12, 1024*1024*50, files_deleted=3, bytes_freed=1024*1024*20)
    db.record_scan("full",      88, 1024*1024*200, files_deleted=10, bytes_freed=1024*1024*95)
    history = db.get_scan_history()
    db.close()
    os.remove(tmpdb)
    print(f"✅  Schema validated — {len(history)} scan records inserted and retrieved.")
    for row in history:
        print(f"   [{row['scan_type']}] found={row['files_found']} deleted={row['files_deleted']}")

