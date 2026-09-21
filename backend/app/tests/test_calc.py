import app.db as db
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.seed import init_db
from app.services.taxi_service import TaxiService

T = {"start_price": 11, "start_include_km": 3, "per_km": 2.5, "per_slow_min": 0.8, "night_factor": 1.2}
EXPECTED_TOTAL = 17.6


def test_day_short():
    r = calc_fare(5, 2, False, T)
    assert r["total"] == 17.6
    assert r["mileage"] == 5.0


def test_day_breakdown():
    r = calc_fare(5, 2, False, T)
    assert r["start"] == 11, f"起步费不符: 得到 {r['start']}, 期望 11"
    assert r["mileage"] == 5.0, f"里程费不符: 得到 {r['mileage']}, 期望 5.0"
    assert r["slow_fee"] == 1.6, f"低速费不符: 得到 {r['slow_fee']}, 期望 1.6"
    assert r["total"] == EXPECTED_TOTAL, (
        f"应付不符: 得到的应付 {r['total']}, 期望应付 {EXPECTED_TOTAL}"
    )
    parts_total = round(r["start"] + r["mileage"] + r["slow_fee"], 2)
    assert parts_total == r["total"], (
        f"三项之和不等于应付: 得到的应付 {parts_total}, 期望应付 {r['total']}"
    )


def test_night_long():
    r = calc_fare(18, 12, True, T)
    assert r["total"] == 69.72


def test_compare_delta():
    c = compare_day_night(18, 12, T)
    assert c["night_total"] > c["day_total"]


def _count_runs():
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
    finally:
        conn.close()


def test_fare_persist_isolated(tmp_path, monkeypatch):
    # 等价隔离库：把连接指向临时目录中的数据库，不触碰默认数据文件
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    init_db()

    with TaxiService() as s:
        before = _count_runs()

        no_persist = s.fare(5, 2, False, None, persist=False)
        assert no_persist["run_id"] is None, (
            f"persist 为假时不应返回 run_id, 得到 {no_persist['run_id']}"
        )
        assert no_persist["total"] == EXPECTED_TOTAL, (
            f"persist 为假时应付不符: 得到的应付 {no_persist['total']}, 期望应付 {EXPECTED_TOTAL}"
        )
        assert _count_runs() == before, (
            f"persist 为假时不应落库: 得到条数 {_count_runs()}, 期望条数 {before}"
        )

        persisted = s.fare(5, 2, False, None, persist=True)
        assert persisted["run_id"] is not None, "persist 为真时应返回 run_id"
        assert persisted["total"] == EXPECTED_TOTAL, (
            f"persist 为真时应付不符: 得到的应付 {persisted['total']}, 期望应付 {EXPECTED_TOTAL}"
        )
        assert _count_runs() == before + 1, (
            f"persist 为真时应新增一条记录: 得到条数 {_count_runs()}, 期望条数 {before + 1}"
        )
