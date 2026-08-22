"""
End-to-End Integration Test: Forecasting Pipeline -> Canonical Network -> MILP Solver.
"""

import pandas as pd
import pytest

from netgravity.forecasting.agent import ForecastingAgent
from netgravity.forecasting.schemas import DemandPoint, DemandTimeSeries
from netgravity.optimization.milp import milp_solve
from netgravity.schemas.network import (
    CanonicalNetwork,
    CostPeriod,
    DemandRecord,
    FacilityRecord,
    FacilityStatus,
    LaneRecord,
    NodeRole,
    OptimizationConfig,
    ProductRecord,
    TransportMode,
)


@pytest.fixture
def sample_network():
    """Minimal viable 2-facility, 2-market canonical network."""
    facilities = [
        FacilityRecord(
            id="PLANT_1",
            name="Plant 1",
            role=NodeRole.PLANT,
            status=FacilityStatus.EXISTING,
            latitude=19.0760,
            longitude=72.8777,
            capacity_units_per_period=50000.0,
            production_capacity_units_per_period=50000.0,
            fixed_cost_per_year=120000.0,
            handling_cost_per_unit=5.0,
        ),
        FacilityRecord(
            id="DC_1",
            name="DC 1",
            role=NodeRole.DC,
            status=FacilityStatus.EXISTING,
            latitude=28.7041,
            longitude=77.1025,
            capacity_units_per_period=40000.0,
            fixed_cost_per_year=60000.0,
            handling_cost_per_unit=3.0,
        ),
        FacilityRecord(
            id="M_MUMBAI",
            name="Mumbai Market",
            role=NodeRole.MARKET,
            status=FacilityStatus.EXISTING,
            latitude=19.0760,
            longitude=72.8777,
            capacity_units_per_period=1e9,
        ),
        FacilityRecord(
            id="M_DELHI",
            name="Delhi Market",
            role=NodeRole.MARKET,
            status=FacilityStatus.EXISTING,
            latitude=28.7041,
            longitude=77.1025,
            capacity_units_per_period=1e9,
        ),
    ]

    products = [
        ProductRecord(
            id="SKU_A",
            name="Widget A",
            unit_value=50.0,
            holding_rate=0.20,
            target_service_level=0.95,
        ),
    ]

    lanes = [
        LaneRecord(
            origin_id="PLANT_1",
            destination_id="DC_1",
            mode=TransportMode.ROAD,
            distance_km=1400.0,
            rate_per_unit=15.0,
            transit_time_days=3.0,
        ),
        LaneRecord(
            origin_id="DC_1",
            destination_id="M_DELHI",
            mode=TransportMode.ROAD,
            distance_km=50.0,
            rate_per_unit=2.0,
            transit_time_days=0.5,
        ),
        LaneRecord(
            origin_id="PLANT_1",
            destination_id="M_MUMBAI",
            mode=TransportMode.ROAD,
            distance_km=40.0,
            rate_per_unit=2.0,
            transit_time_days=0.5,
        ),
    ]

    demands = [
        DemandRecord(market_id="M_MUMBAI", product_id="SKU_A", period=1, quantity=1000.0, std_dev=50.0),
        DemandRecord(market_id="M_DELHI", product_id="SKU_A", period=1, quantity=800.0, std_dev=40.0),
    ]

    config = OptimizationConfig(cost_period=CostPeriod.MONTH)

    return CanonicalNetwork(
        network_id="test_net",
        facilities=facilities,
        products=products,
        lanes=lanes,
        demands=demands,
        config=config,
    )


def test_end_to_end_forecasting_to_milp(sample_network):
    # Step 1: Simulated raw history from Extraction Agent
    df_raw = pd.DataFrame([
        # Mumbai history
        {"market_id": "M_MUMBAI", "product_id": "SKU_A", "period": i, "quantity": 1000 + i * 15}
        for i in range(1, 13)
    ] + [
        # Delhi history
        {"market_id": "M_DELHI", "product_id": "SKU_A", "period": i, "quantity": 800 + i * 10}
        for i in range(1, 13)
    ])

    agent = ForecastingAgent()
    
    # Step 2: Forecast with external market surge signal
    signal = "Diwali festival surge promotion across all markets"
    forecasts = agent.forecast_from_dataframe(df_raw, horizon=2, external_signal_text=signal)

    assert len(forecasts) == 2
    for fc in forecasts:
        assert fc.total_expected_demand > 0
        assert fc.signal_applied is not None
        assert fc.signal_applied.demand_multiplier > 1.0

    # Step 3: Update CanonicalNetwork with period 1 forecast
    updated_network = agent.update_network_demands(sample_network, forecasts, period_index=1)
    
    # Verify demands updated
    mumbai_demand = next(d for d in updated_network.demands if d.market_id == "M_MUMBAI")
    assert mumbai_demand.quantity > 1000.0
    assert mumbai_demand.std_dev > 0.0

    # Step 4: Solve MILP using the forecasted demand network
    solution = milp_solve(updated_network)

    assert solution.solver.status in ("OPTIMAL", "FEASIBLE")
    assert solution.solver.objective_value > 0.0


def test_scenario_variation_generation(sample_network):
    agent = ForecastingAgent()
    ts_list = [
        DemandTimeSeries(
            market_id="M_MUMBAI",
            product_id="SKU_A",
            history=[DemandPoint(period=i, quantity=500.0) for i in range(1, 10)],
        )
    ]
    forecasts = agent.forecast_dataset(ts_list, horizon=1)
    scenarios = agent.generate_scenario_variations(sample_network, forecasts, period_index=1)

    assert "p10_conservative" in scenarios
    assert "p50_expected" in scenarios
    assert "p90_surge" in scenarios

    p10_d = next(d for d in scenarios["p10_conservative"].demands if d.market_id == "M_MUMBAI")
    p50_d = next(d for d in scenarios["p50_expected"].demands if d.market_id == "M_MUMBAI")
    p90_d = next(d for d in scenarios["p90_surge"].demands if d.market_id == "M_MUMBAI")

    assert p10_d.quantity <= p50_d.quantity <= p90_d.quantity
