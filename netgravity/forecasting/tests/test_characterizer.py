"""
Tests for Demand Pattern Characterizer (ADI vs CV²).
"""

import pytest
from netgravity.forecasting.characterizer import compute_demand_metrics
from netgravity.forecasting.schemas import DemandPattern


def test_smooth_demand():
    # Regular continuous demand with low variance
    quantities = [100, 105, 98, 102, 101, 99, 104, 100, 102, 97, 101, 103]
    metrics = compute_demand_metrics(quantities)
    assert metrics.pattern == DemandPattern.SMOOTH
    assert metrics.adi == 1.0
    assert metrics.cv2 < 0.49
    assert metrics.zero_ratio == 0.0


def test_intermittent_demand():
    # Sporadic non-zero demand with constant/low-variance sizing
    quantities = [0, 50, 0, 0, 52, 0, 48, 0, 0, 50, 0, 0]
    metrics = compute_demand_metrics(quantities)
    assert metrics.pattern == DemandPattern.INTERMITTENT
    assert metrics.adi >= 1.32
    assert metrics.cv2 < 0.49


def test_erratic_demand():
    # Continuous non-zero demand with high variance
    quantities = [10, 500, 20, 800, 15, 600, 30, 900, 25, 750]
    metrics = compute_demand_metrics(quantities)
    assert metrics.pattern == DemandPattern.ERRATIC
    assert metrics.adi < 1.32
    assert metrics.cv2 >= 0.49


def test_lumpy_demand():
    # Sporadic demand with high variance in sizes
    quantities = [0, 10, 0, 0, 600, 0, 0, 0, 50, 0, 1200, 0]
    metrics = compute_demand_metrics(quantities)
    assert metrics.pattern == DemandPattern.LUMPY
    assert metrics.adi >= 1.32
    assert metrics.cv2 >= 0.49


def test_cold_start_demand():
    # Very short history (< 8 data points)
    quantities = [100, 120, 110]
    metrics = compute_demand_metrics(quantities)
    assert metrics.pattern == DemandPattern.COLD_START
    assert metrics.total_periods == 3
