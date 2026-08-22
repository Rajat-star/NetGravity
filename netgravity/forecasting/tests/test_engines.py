"""
Tests for Forecasting Engines (Intermittent, Quantile, ETS, Foundation).
"""

import pytest
from netgravity.forecasting.engines.auto_selector import AutoModelSelector
from netgravity.forecasting.engines.ets_smoother import AutoETSForecaster
from netgravity.forecasting.engines.foundation_adapter import FoundationZeroShotForecaster
from netgravity.forecasting.engines.intermittent import IntermittentForecaster
from netgravity.forecasting.engines.quantile_regressor import QuantileRegressionForecaster
from netgravity.forecasting.schemas import DemandPoint, DemandTimeSeries


def make_ts(quantities, m_id="M_MUMBAI", p_id="SKU_1"):
    points = [DemandPoint(period=i + 1, quantity=float(q)) for i, q in enumerate(quantities)]
    return DemandTimeSeries(market_id=m_id, product_id=p_id, history=points)


def test_intermittent_sba():
    quantities = [0, 20, 0, 0, 22, 0, 18, 0, 0, 20, 0, 0]
    ts = make_ts(quantities)
    engine = IntermittentForecaster(method="SBA")
    res = engine.fit_predict(ts, horizon=3)

    assert len(res.horizon_points) == 3
    assert res.horizon_points[0].mean > 0.0
    assert res.horizon_points[0].p10 <= res.horizon_points[0].p50 <= res.horizon_points[0].p90
    assert res.horizon_points[0].p10 == 0.0  # Zero-inflated quantile check


def test_ets_smoother_trend():
    # Linear upward trend series
    quantities = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210]
    ts = make_ts(quantities)
    engine = AutoETSForecaster()
    res = engine.fit_predict(ts, horizon=2)

    assert len(res.horizon_points) == 2
    assert res.horizon_points[0].mean > 200.0
    assert res.horizon_points[0].p10 < res.horizon_points[0].mean < res.horizon_points[0].p90


def test_quantile_regressor():
    quantities = [50, 55, 48, 52, 60, 65, 58, 62, 70, 75, 68, 72, 80, 85, 78, 82]
    ts = make_ts(quantities)
    engine = QuantileRegressionForecaster()
    res = engine.fit_predict(ts, horizon=4)

    assert len(res.horizon_points) == 4
    for pt in res.horizon_points:
        assert pt.p10 <= pt.p50 <= pt.p90
        assert pt.std_dev > 0.0


def test_foundation_cold_start():
    # 3 periods of history
    quantities = [300, 320, 310]
    ts = make_ts(quantities)
    engine = FoundationZeroShotForecaster()
    res = engine.fit_predict(ts, horizon=2)

    assert len(res.horizon_points) == 2
    assert 250.0 < res.horizon_points[0].mean < 350.0
    assert res.horizon_points[0].p10 <= res.horizon_points[0].mean <= res.horizon_points[0].p90


def test_auto_model_selector_routing():
    selector = AutoModelSelector()

    # Intermittent
    interm_ts = make_ts([0, 10, 0, 0, 12, 0, 0, 10, 0, 0, 11, 0])
    res_interm = selector.fit_predict(interm_ts, horizon=1)
    assert "Intermittent" in res_interm.engine_name

    # Cold Start
    cold_ts = make_ts([50, 60])
    res_cold = selector.fit_predict(cold_ts, horizon=1)
    assert "ZeroShot" in res_cold.engine_name or "Foundation" in res_cold.engine_name
