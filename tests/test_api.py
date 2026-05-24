"""Tests for the ThreadTrack API.

Each test runs against a fresh temporary SQLite file so persistence
behaviour is exercised without polluting the development DB.
"""

import importlib
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """API client backed by an empty, throwaway SQLite file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("THREADTRACK_DB_PATH", tmp.name)

    # Reload so DB_PATH picks up the env var; skip CSV seeding for tests.
    from api import db as db_mod
    importlib.reload(db_mod)
    from api import main as main_mod
    importlib.reload(main_mod)
    main_mod.SCORED_CSV = type("FakePath", (), {"exists": lambda self: False})()

    with TestClient(main_mod.app) as c:
        yield c
    os.unlink(tmp.name)


LOW_RISK = {
    "vendor_is_new": False, "vendor_cluster": "Bengaluru",
    "vendor_reliability": 0.93, "fabric_type": "knit", "order_qty": 100,
    "destination_tier": "Tier-1", "payment_mode": "Prepaid", "season": "normal",
}

HIGH_RISK = {
    "vendor_is_new": True, "vendor_cluster": "Tirupur",
    "vendor_reliability": 0.75, "fabric_type": "woven", "order_qty": 400,
    "destination_tier": "Tier-3", "payment_mode": "COD", "season": "festive",
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_score_returns_bands_and_reasons(client):
    r = client.post("/score", json=HIGH_RISK)
    assert r.status_code == 200
    data = r.json()
    assert 0 <= data["delay_score"] <= 100
    assert 0 <= data["return_score"] <= 100
    assert data["delay_band"] in {"Low", "Medium", "High"}
    assert data["return_band"] in {"Low", "Medium", "High"}
    assert len(data["delay_reasons"]) >= 1
    assert len(data["return_reasons"]) >= 1


def test_score_validates_input(client):
    """Pydantic should reject an order with reliability outside [0, 1]."""
    bad = dict(LOW_RISK, vendor_reliability=1.5)
    r = client.post("/score", json=bad)
    assert r.status_code == 422


def test_create_order_persists_and_returns_scores(client):
    r = client.post("/orders", json=LOW_RISK)
    assert r.status_code == 201
    data = r.json()
    assert data["po_id"].startswith("API-")
    assert data["delay_score"] is not None
    assert data["return_score"] is not None

    # Retrievable by id
    r2 = client.get(f"/orders/{data['po_id']}")
    assert r2.status_code == 200
    assert r2.json()["po_id"] == data["po_id"]


def test_list_orders_filters_by_cluster(client):
    for cluster in ("Tirupur", "Bengaluru"):
        client.post("/orders", json=dict(LOW_RISK, vendor_cluster=cluster))
    r = client.get("/orders?vendor_cluster=Tirupur")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) >= 1
    assert all(o["vendor_cluster"] == "Tirupur" for o in orders)


def test_capture_outcome_then_appears_on_order(client):
    po_id = client.post("/orders", json=LOW_RISK).json()["po_id"]
    r = client.post(f"/orders/{po_id}/outcome",
                    json={"is_delayed": True, "is_returned": False})
    assert r.status_code == 200
    data = r.json()
    assert data["is_delayed"] is True
    assert data["is_returned"] is False


def test_outcome_for_unknown_order_returns_404(client):
    r = client.post("/orders/DOES-NOT-EXIST/outcome",
                    json={"is_delayed": True, "is_returned": False})
    assert r.status_code == 404


def test_get_unknown_order_returns_404(client):
    r = client.get("/orders/NOPE-1234")
    assert r.status_code == 404
