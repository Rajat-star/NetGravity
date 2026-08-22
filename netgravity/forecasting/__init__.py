"""
NetGravity — AI Forecasting Package
===================================
Industry-agnostic, low-token hybrid forecasting engine with direct MILP solver integration.
"""

from netgravity.forecasting.agent import ForecastingAgent
from netgravity.forecasting.characterizer import characterize_series, compute_demand_metrics
from netgravity.forecasting.schemas import (
    DemandPattern,
    DemandPoint,
    DemandTimeSeries,
    ExternalSignalModifier,
    ForecastPoint,
    ForecastResult,
)
from netgravity.forecasting.bridge.milp_bridge import (
    forecast_to_demand_records,
    generate_scenario_networks,
    update_network_with_forecast,
)

__all__ = [
    "ForecastingAgent",
    "characterize_series",
    "compute_demand_metrics",
    "DemandPattern",
    "DemandPoint",
    "DemandTimeSeries",
    "ForecastPoint",
    "ForecastResult",
    "ExternalSignalModifier",
    "forecast_to_demand_records",
    "update_network_with_forecast",
    "generate_scenario_networks",
]
