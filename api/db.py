"""api/db.py — SQLite setup for the ThreadTrack API.

A deliberately minimal data layer: a single connection helper, schema
creation, and a one-shot seed from data/scored_pos.csv so the API starts
with a working dataset on first run.

For a production system this would be Postgres with proper migrations,
connection pooling, and per-brand tenant isolation. For the portfolio
sketch, SQLite in a single file makes the architecture point clearly
with zero infrastructure cost.
"""

import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "THREADTRACK_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "threadtrack.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    po_id                         TEXT PRIMARY KEY,
    po_date                       TEXT NOT NULL,
    vendor_id                     TEXT,
    vendor_is_new                 INTEGER NOT NULL,
    vendor_cluster                TEXT NOT NULL,
    vendor_reliability            REAL NOT NULL,
    fabric_type                   TEXT NOT NULL,
    order_qty                     INTEGER NOT NULL,
    destination_city              TEXT,
    destination_tier              TEXT NOT NULL,
    payment_mode                  TEXT NOT NULL,
    season                        TEXT NOT NULL,
    sampling_delay_days           INTEGER DEFAULT 0,
    fabric_arrival_delay_days     INTEGER DEFAULT 0,
    trims_confirmation_lag_days   INTEGER DEFAULT 0,
    factory_ncr_count             INTEGER DEFAULT 0,
    buyer_change_frequency        INTEGER DEFAULT 1,
    delay_score                   INTEGER,
    return_score                  INTEGER,
    scored_at                     TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    po_id           TEXT PRIMARY KEY,
    is_delayed      INTEGER NOT NULL,
    is_returned     INTEGER NOT NULL,
    captured_at     TEXT NOT NULL,
    FOREIGN KEY (po_id) REFERENCES orders(po_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_cluster ON orders(vendor_cluster);
CREATE INDEX IF NOT EXISTS idx_orders_season  ON orders(season);
"""


def get_connection(db_path=None):
    """Open a SQLite connection with row factory + foreign keys enabled."""
    path = db_path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    """Create the schema if it does not exist. Safe to call repeatedly."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_from_csv(csv_path, db_path=None, limit=None):
    """Seed the orders table from a CSV. No-op if rows already present."""
    import pandas as pd

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if count > 0:
            return count

        df = pd.read_csv(csv_path)
        if limit:
            df = df.head(limit)

        for col, default in [
            ("vendor_id", ""),
            ("destination_city", ""),
            ("sampling_delay_days", 0),
            ("fabric_arrival_delay_days", 0),
            ("trims_confirmation_lag_days", 0),
            ("factory_ncr_count", 0),
            ("buyer_change_frequency", 1),
        ]:
            if col not in df.columns:
                df[col] = default

        def _int_or_none(v):
            return None if pd.isna(v) else int(v)

        rows = []
        for _, row in df.iterrows():
            rows.append((
                row["po_id"],
                str(row["po_date"]),
                row.get("vendor_id", "") or "",
                int(bool(row["vendor_is_new"])),
                row["vendor_cluster"],
                float(row["vendor_reliability"]),
                row["fabric_type"],
                int(row["order_qty"]),
                row.get("destination_city", "") or "",
                row["destination_tier"],
                row["payment_mode"],
                row["season"],
                int(row.get("sampling_delay_days", 0) or 0),
                int(row.get("fabric_arrival_delay_days", 0) or 0),
                int(row.get("trims_confirmation_lag_days", 0) or 0),
                int(row.get("factory_ncr_count", 0) or 0),
                int(row.get("buyer_change_frequency", 1) or 1),
                _int_or_none(row.get("delay_score")) if "delay_score" in df.columns else None,
                _int_or_none(row.get("return_score")) if "return_score" in df.columns else None,
                str(row.get("po_date", "")),
            ))

        conn.executemany(
            """INSERT INTO orders (po_id, po_date, vendor_id, vendor_is_new,
                vendor_cluster, vendor_reliability, fabric_type, order_qty,
                destination_city, destination_tier, payment_mode, season,
                sampling_delay_days, fabric_arrival_delay_days,
                trims_confirmation_lag_days, factory_ncr_count,
                buyer_change_frequency, delay_score, return_score, scored_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()
