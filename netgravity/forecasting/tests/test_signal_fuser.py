"""
Tests for External Signal Fuser.
"""

import pytest
from netgravity.forecasting.schemas import DemandPoint, DemandTimeSeries
from netgravity.forecasting.engines.ets_smoother import AutoETSForecaster
from netgravity.forecasting.signals.fuser import ExternalSignalFuser


def test_signal_fuser_surge():
    fuser = ExternalSignalFuser()
    signal_text = "Major Diwali festival sales promotion expected across north and west zones"
    mod = fuser.extract_modifier_from_text(signal_text)

    assert mod.demand_multiplier > 1.0
    assert "surge" in mod.reasoning.lower() or "festival" in mod.reasoning.lower()


def test_signal_fuser_disruption():
    fuser = ExternalSignalFuser()
    signal_text = "Severe port congestion and trucker strike causing delays"
    mod = fuser.extract_modifier_from_text(signal_text)

    assert mod.lead_time_delta_days > 0.0
    assert mod.std_dev_multiplier > 1.0


def test_apply_signal_modifier():
    fuser = ExternalSignalFuser()
    ts = DemandTimeSeries(
        market_id="M_DELHI",
        product_id="SKU_BEV",
        history=[DemandPoint(period=i + 1, quantity=100.0) for i in range(12)],
    )
    engine = AutoETSForecaster()
    base_res = engine.fit_predict(ts, horizon=2)

    mod = fuser.extract_modifier_from_text("Festival holiday boom")
    adj_res = fuser.apply_modifier(base_res, mod)

    assert adj_res.horizon_points[0].mean > base_res.horizon_points[0].mean
    assert adj_res.signal_applied is not None
