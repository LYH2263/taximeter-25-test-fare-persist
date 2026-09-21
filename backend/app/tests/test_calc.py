import app.db
from app.db import connect
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.seed import init_db
from app.services.taxi_service import TaxiService

T = {"start_price": 11, "start_include_km": 3, "per_km": 2.5, "per_slow_min": 0.8, "night_factor": 1.2}

def test_day_short():
    r = calc_fare(5, 2, False, T)
    assert r["total"] == 17.6
    assert r["mileage"] == 5.0
    assert r["start"] == 11
    assert r["slow_fee"] == 1.6
    assert r["start"] + r["mileage"] + r["slow_fee"] == r["total"]

def test_night_long():
    r = calc_fare(18, 12, True, T)
    assert r["total"] == 69.72

def test_compare_delta():
    c = compare_day_night(18, 12, T)
    assert c["night_total"] > c["day_total"]

def test_fare_persist_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(app.db, "DB_PATH", tmp_path / "test.db")
    init_db()

    def run_count():
        return connect().execute("SELECT COUNT(*) FROM calc_runs").fetchone()[0]

    with TaxiService() as svc:
        before = run_count()
        r1 = svc.fare(5, 2, False, None, False)
        assert r1["run_id"] is None
        assert run_count() == before
        assert r1["total"] == 17.6, f"persist=False 应付={r1['total']} 期望=17.6"

        r2 = svc.fare(5, 2, False, None, True)
        assert r2["run_id"] is not None
        assert run_count() == before + 1
        assert r2["total"] == 17.6, f"persist=True 应付={r2['total']} 期望=17.6"
