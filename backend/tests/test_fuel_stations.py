"""
tests/test_fuel_stations.py

Unit and integration tests for the Fuel Station Availability feature.

Test coverage:
  - Confidence decay at 0h / 1h / 2h / 4h / >4h (operator source)
  - Crowdsource max confidence cap (80%)
  - Operator registration stub flow
  - OTP stub accepts any value
  - Availability update appends a new row (never overwrites)
  - Debug simulate-time: blocked without DEMO_MODE, works with DEMO_MODE=true
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.confidence import calculate_confidence, get_best_confidence
from tests.conftest import TestingSessionLocal, create_test_user


# ── Pure confidence calculation tests (no DB needed) ─────────────────────────

class TestConfidenceDecay:
    """Tests for the pure confidence calculation service."""

    def _now(self):
        return datetime.now(timezone.utc)

    def _ts(self, hours_ago: float) -> datetime:
        return self._now() - timedelta(hours=hours_ago)

    def test_operator_confidence_at_0hr(self):
        """Immediately after an operator update, score should be 100."""
        result = calculate_confidence(self._ts(0), source="operator", current_time=self._now())
        assert result["score"] == 100
        assert result["is_stale"] is False

    def test_operator_confidence_at_1hr(self):
        """After 1 hour, operator confidence should be ~75% (25% decayed of 4h window)."""
        ts = self._ts(1)
        result = calculate_confidence(ts, source="operator", current_time=self._now())
        # linear decay: 100 * (1 - 1/4) = 75
        assert 70 <= result["score"] <= 80  # slight tolerance for rounding

    def test_operator_confidence_at_2hr(self):
        """After 2 hours, operator confidence should be ~50%."""
        ts = self._ts(2)
        result = calculate_confidence(ts, source="operator", current_time=self._now())
        assert 45 <= result["score"] <= 55

    def test_operator_confidence_at_4hr(self):
        """After exactly 4 hours, operator confidence should be 0 (fully decayed)."""
        ts = self._ts(4)
        result = calculate_confidence(ts, source="operator", current_time=self._now())
        assert result["score"] == 0
        assert result["is_stale"] is True

    def test_operator_confidence_past_4hr(self):
        """After 5+ hours, confidence is 0 and is_stale=True."""
        ts = self._ts(5.5)
        result = calculate_confidence(ts, source="operator", current_time=self._now())
        assert result["score"] == 0
        assert result["is_stale"] is True
        assert result["label"] == "Data expired"

    def test_crowdsource_max_score_80(self):
        """Crowdsource update at time=0 should cap at 80%, not 100%."""
        result = calculate_confidence(self._ts(0), source="crowdsource", current_time=self._now())
        assert result["score"] <= 80
        assert result["score"] >= 75  # should be ~80 at t=0

    def test_crowdsource_decay_faster(self):
        """After 1.5 hours, crowdsource confidence should be 0 (faster decay window)."""
        ts = self._ts(1.5)
        result = calculate_confidence(
            ts, source="crowdsource", current_time=self._now(),
            crowdsource_decay_hours=1.5
        )
        assert result["score"] == 0
        assert result["is_stale"] is True

    def test_freshness_label_just_confirmed(self):
        result = calculate_confidence(self._ts(0), source="operator", current_time=self._now())
        assert "Just confirmed" in result["label"] or "Confirmed" in result["label"]

    def test_get_best_confidence_empty(self):
        """No updates → score=0, is_stale=True, no data label."""
        result = get_best_confidence([])
        assert result["score"] == 0
        assert result["is_stale"] is True
        assert result["label"] == "No data"


# ── API integration tests ─────────────────────────────────────────────────────

class TestOperatorRegistration:
    def test_register_operator_stub(self, client):
        """POST /api/stations/operators/register should succeed and return demo status."""
        payload = {
            "station_name": "Test Pump NH48",
            "station_latitude": 27.71,
            "station_longitude": 76.20,
            "route_tag": "NH48-Jaipur-Delhi",
            "fuel_types_offered": ["petrol", "diesel"],
            "operator_name": "Test Owner",
            "phone_number": "9800000002",
            "license_number": "TEST-LIC-0002",
        }
        resp = client.post("/api/stations/operators/register", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification_status"] == "demo"
        assert "api_key" in data
        assert data["station_id"] is not None

    def test_register_invalid_fuel_type(self, client):
        """Registering with an invalid fuel_type should return 422."""
        payload = {
            "station_name": "Bad Pump",
            "station_latitude": 27.71,
            "station_longitude": 76.20,
            "fuel_types_offered": ["rocket_fuel"],   # invalid
            "operator_name": "Bad Owner",
            "phone_number": "9800000003",
        }
        resp = client.post("/api/stations/operators/register", json=payload)
        assert resp.status_code == 422


class TestOTPStub:
    def test_otp_stub_accepts_any_code(self, client, db_session):
        """POST /api/stations/operators/{id}/verify-otp should accept any OTP."""
        # First create an operator via registration
        from app.models.models import FuelStation, FuelStationOperator
        station = FuelStation(name="OTP Test", latitude=27.0, longitude=76.0, is_demo=True)
        db_session.add(station)
        db_session.flush()
        op = FuelStationOperator(
            station_id=station.id, name="OTP Op", phone_number="9800000010",
            verification_status="demo", api_key="otp-test-key"
        )
        db_session.add(op)
        db_session.commit()
        db_session.refresh(op)

        resp = client.post(
            f"/api/stations/operators/{op.id}/verify-otp",
            json={"otp": "any-value-at-all-123"}
        )
        assert resp.status_code == 200
        assert "stub" in resp.json()["note"].lower()


class TestAvailabilityLog:
    def _create_station_and_operator(self, db: Session):
        """Helper: create a demo station + operator and return them."""
        from app.models.models import FuelStation, StationFuelType, FuelStationOperator
        station = FuelStation(
            name="Log Test Station", latitude=27.7, longitude=76.2,
            route_tag="NH48-Jaipur-Delhi", is_demo=True
        )
        db.add(station)
        db.flush()
        db.add(StationFuelType(station_id=station.id, fuel_type="petrol", is_offered=True))
        op = FuelStationOperator(
            station_id=station.id, name="Log Op", phone_number="9800000020",
            verification_status="demo", api_key="log-test-key-xyz"
        )
        db.add(op)
        db.commit()
        db.refresh(station)
        return station, op

    def test_availability_appends_new_row(self, client, db_session):
        """Each POST to /availability should INSERT a new row, never overwrite."""
        from app.models.models import AvailabilityUpdate
        station, op = self._create_station_and_operator(db_session)

        headers = {"X-Operator-Key": op.api_key}
        payload = {"fuel_type": "petrol", "reported_status": "available"}

        # Post the same update twice
        r1 = client.post(f"/api/stations/{station.id}/availability", json=payload, headers=headers)
        r2 = client.post(f"/api/stations/{station.id}/availability", json=payload, headers=headers)

        assert r1.status_code == 200
        assert r2.status_code == 200

        # Should now have 2 rows in the log (not 1 overwritten row)
        count = db_session.query(AvailabilityUpdate).filter(
            AvailabilityUpdate.station_id == station.id,
            AvailabilityUpdate.fuel_type == "petrol",
        ).count()
        assert count == 2, f"Expected 2 rows (append-only), got {count}"

    def test_availability_wrong_operator_key_rejected(self, client, db_session):
        """Wrong X-Operator-Key should be rejected with 401."""
        station, _ = self._create_station_and_operator(db_session)
        resp = client.post(
            f"/api/stations/{station.id}/availability",
            json={"fuel_type": "petrol", "reported_status": "available"},
            headers={"X-Operator-Key": "totally-wrong-key"},
        )
        assert resp.status_code == 401


class TestDebugEndpoint:
    def _setup_station_with_update(self, db_session: Session):
        from app.models.models import FuelStation, StationFuelType, FuelStationOperator, AvailabilityUpdate
        station = FuelStation(
            name="Debug Test", latitude=27.7, longitude=76.2,
            route_tag="NH48-Jaipur-Delhi", is_demo=True
        )
        db_session.add(station)
        db_session.flush()
        db_session.add(StationFuelType(station_id=station.id, fuel_type="petrol", is_offered=True))
        op = FuelStationOperator(
            station_id=station.id, name="Debug Op", phone_number="9800000030",
            verification_status="demo", api_key="debug-test-key"
        )
        db_session.add(op)
        db_session.flush()
        db_session.add(AvailabilityUpdate(
            station_id=station.id, fuel_type="petrol",
            source="operator", reported_status="available",
            reported_at=datetime.now(timezone.utc), reported_by=op.id
        ))
        db_session.commit()
        db_session.refresh(station)
        return station

    def test_debug_blocked_without_demo_mode(self, client, db_session, monkeypatch):
        """Simulate-time endpoint should return 403 when DEMO_MODE is false."""
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "demo_mode", False)

        station = self._setup_station_with_update(db_session)
        resp = client.post("/api/debug/simulate-time", json={"station_id": station.id, "shift_hours": 2})
        assert resp.status_code == 403

    def test_debug_shifts_timestamp_with_demo_mode(self, client, db_session, monkeypatch):
        """With DEMO_MODE=true, simulate-time should shift reported_at backward."""
        from app.core import config as cfg
        from app.models.models import AvailabilityUpdate
        monkeypatch.setattr(cfg.settings, "demo_mode", True)

        station = self._setup_station_with_update(db_session)

        # Record the original reported_at
        original_update = db_session.query(AvailabilityUpdate).filter(
            AvailabilityUpdate.station_id == station.id
        ).first()
        original_at = original_update.reported_at

        resp = client.post(
            "/api/debug/simulate-time",
            json={"station_id": station.id, "shift_hours": 3.0}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["shift_hours"] == 3.0
        assert data["rows_affected"] >= 1

        # Refresh and verify the timestamp was shifted back by ~3h
        db_session.expire_all()
        updated = db_session.query(AvailabilityUpdate).filter(
            AvailabilityUpdate.station_id == station.id
        ).first()
        shifted_at = updated.reported_at
        if shifted_at.tzinfo is None:
            shifted_at = shifted_at.replace(tzinfo=timezone.utc)
        if original_at.tzinfo is None:
            original_at = original_at.replace(tzinfo=timezone.utc)

        diff_seconds = (original_at - shifted_at).total_seconds()
        # Should be approximately 3 hours (allow ±30 seconds tolerance for test timing)
        assert 3 * 3600 - 30 <= diff_seconds <= 3 * 3600 + 30, \
            f"Expected ~3h shift, got {diff_seconds}s"
