"""api/main.py — the ThreadTrack API.

A FastAPI service that exposes the rule scorer, the hybrid (rule + ML)
scorer, and CRUD over orders + realised outcomes. SQLite under the hood
for the portfolio sketch; the layer above (scorer logic, the hybrid
blend) is reused unchanged from src/, demonstrating that the scoring
core was already backend-shaped (pure functions, data in / data out).

Run locally:
    uvicorn api.main:app --reload --port 8000

Then visit http://localhost:8000/docs for the OpenAPI explorer.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from api.db import get_connection, init_db, seed_from_csv
from api.models import (
    HybridScoreOutput,
    OrderInput,
    OrderOut,
    OutcomeInput,
    ScoreOutput,
)
from src.rule_scorer import score_order

SCORED_CSV = Path(__file__).resolve().parent.parent / "data" / "scored_pos.csv"
VERSION = "0.1.0"


def _band(score):
    if score <= 35:
        return "Low"
    if score <= 65:
        return "Medium"
    return "High"


def _utcnow():
    return datetime.now(timezone.utc)


def _to_score_output(order_dict):
    """Run the rule scorer, wrap into the API response shape."""
    r = score_order(order_dict)
    return ScoreOutput(
        delay_score=r["delay_score"],
        return_score=r["return_score"],
        delay_band=_band(r["delay_score"]),
        return_band=_band(r["return_score"]),
        delay_reasons=r["delay_reasons"],
        return_reasons=r["return_reasons"],
    )


def get_db():
    """FastAPI dependency that yields a SQLite connection per request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


# Modern FastAPI pattern — Annotated keeps Depends() out of arg defaults
# (which keeps ruff's B008 quiet too) and reads more clearly at call sites.
DbDep = Annotated[Connection, Depends(get_db)]


@asynccontextmanager
async def lifespan(_app):
    """Initialise the database on startup; seed from scored_pos.csv if present."""
    init_db()
    if SCORED_CSV.exists():
        try:
            seed_from_csv(str(SCORED_CSV))
        except Exception as e:  # noqa: BLE001 — seed failures should not block the API
            print(f"WARN: seed from {SCORED_CSV} failed: {e}")
    yield


app = FastAPI(
    title="ThreadTrack API",
    description=(
        "REST surface for the ThreadTrack delay + return risk scorer. "
        "Wraps src.rule_scorer and src.hybrid_scorer over a SQLite "
        "orders + outcomes store. Portfolio-sketch scope."
    ),
    version=VERSION,
    lifespan=lifespan,
)


# -------------------------------------------------------------- endpoints --

@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok", "version": VERSION}


@app.post("/score", response_model=ScoreOutput)
def score(order: OrderInput):
    """Score a single order with the rule scorer. No DB write."""
    return _to_score_output(order.model_dump())


@app.post("/score-hybrid", response_model=HybridScoreOutput)
def score_with_hybrid(order: OrderInput):
    """Score with the rule + ML hybrid. Requires trained models in
    output/models/ — run `make ml` first if you get a 503."""
    try:
        from src.hybrid_scorer import score_hybrid
        r = score_hybrid(order.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Trained ML models not found ({e}). Run `make ml` first.",
        ) from e
    keep = HybridScoreOutput.model_fields.keys()
    return HybridScoreOutput(**{k: v for k, v in r.items() if k in keep})


@app.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderInput, conn: DbDep):
    """Create a new order, score it, persist both, return the persisted row."""
    now = _utcnow()
    po_id = f"API-{uuid.uuid4().hex[:8]}"
    today = now.date().isoformat()
    s = _to_score_output(order.model_dump())

    conn.execute(
        """INSERT INTO orders (po_id, po_date, vendor_id, vendor_is_new,
            vendor_cluster, vendor_reliability, fabric_type, order_qty,
            destination_city, destination_tier, payment_mode, season,
            sampling_delay_days, fabric_arrival_delay_days,
            trims_confirmation_lag_days, factory_ncr_count,
            buyer_change_frequency, delay_score, return_score, scored_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (po_id, today, order.vendor_id, int(order.vendor_is_new),
         order.vendor_cluster, order.vendor_reliability, order.fabric_type,
         order.order_qty, order.destination_city, order.destination_tier,
         order.payment_mode, order.season, order.sampling_delay_days,
         order.fabric_arrival_delay_days, order.trims_confirmation_lag_days,
         order.factory_ncr_count, order.buyer_change_frequency,
         s.delay_score, s.return_score, now.isoformat()),
    )
    conn.commit()
    return _fetch_order(conn, po_id)


@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    conn: DbDep,
    vendor_cluster: str | None = None,
    season: str | None = None,
    risk_band: str | None = None,
    limit: int = 50,
):
    """List orders, optionally filtered by cluster, season, or risk band."""
    where, params = [], []
    if vendor_cluster:
        where.append("o.vendor_cluster = ?")
        params.append(vendor_cluster)
    if season:
        where.append("o.season = ?")
        params.append(season)
    if risk_band == "High":
        where.append("o.delay_score > 65")
    elif risk_band == "Medium":
        where.append("o.delay_score > 35 AND o.delay_score <= 65")
    elif risk_band == "Low":
        where.append("o.delay_score <= 35")
    sql = ("SELECT o.*, c.is_delayed, c.is_returned "
           "FROM orders o LEFT JOIN outcomes c ON o.po_id = c.po_id")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY o.delay_score DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_order(r) for r in rows]


@app.get("/orders/{po_id}", response_model=OrderOut)
def get_one_order(po_id: str, conn: DbDep):
    """Get one order with its score and (if captured) realised outcome."""
    order = _fetch_order(conn, po_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@app.post("/orders/{po_id}/outcome", response_model=OrderOut)
def capture_outcome(po_id: str, outcome: OutcomeInput, conn: DbDep):
    """Capture the realised outcome — the data that feeds production retraining."""
    if conn.execute("SELECT po_id FROM orders WHERE po_id = ?",
                    (po_id,)).fetchone() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    conn.execute(
        """INSERT INTO outcomes (po_id, is_delayed, is_returned, captured_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(po_id) DO UPDATE SET
               is_delayed  = excluded.is_delayed,
               is_returned = excluded.is_returned,
               captured_at = excluded.captured_at""",
        (po_id, int(outcome.is_delayed), int(outcome.is_returned),
         _utcnow().isoformat()),
    )
    conn.commit()
    return _fetch_order(conn, po_id)


# ----------------------------------------------------------------- helpers

def _fetch_order(conn, po_id):
    row = conn.execute(
        """SELECT o.*, c.is_delayed, c.is_returned
           FROM orders o LEFT JOIN outcomes c ON o.po_id = c.po_id
           WHERE o.po_id = ?""",
        (po_id,),
    ).fetchone()
    return None if row is None else _row_to_order(row)


def _row_to_order(row):
    return OrderOut(
        po_id=row["po_id"], po_date=row["po_date"],
        vendor_is_new=bool(row["vendor_is_new"]),
        vendor_cluster=row["vendor_cluster"],
        vendor_reliability=row["vendor_reliability"],
        fabric_type=row["fabric_type"], order_qty=row["order_qty"],
        destination_tier=row["destination_tier"],
        payment_mode=row["payment_mode"], season=row["season"],
        sampling_delay_days=row["sampling_delay_days"] or 0,
        fabric_arrival_delay_days=row["fabric_arrival_delay_days"] or 0,
        trims_confirmation_lag_days=row["trims_confirmation_lag_days"] or 0,
        factory_ncr_count=row["factory_ncr_count"] or 0,
        buyer_change_frequency=row["buyer_change_frequency"] or 1,
        delay_score=row["delay_score"],
        return_score=row["return_score"],
        is_delayed=bool(row["is_delayed"]) if row["is_delayed"] is not None else None,
        is_returned=bool(row["is_returned"]) if row["is_returned"] is not None else None,
    )
