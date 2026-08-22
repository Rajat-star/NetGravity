"""
NetGravity — MILP Solver Bridge
===============================
Translates probabilistic forecasts (E[D], σ_D, P10, P50, P90) into canonical
DemandRecord entities and CanonicalNetwork instances ready for mathematical
optimization in NetGravityMILP.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional

from netgravity.forecasting.schemas import ForecastResult
from netgravity.schemas.network import (
    CanonicalNetwork,
    DemandRecord,
)


def forecast_to_demand_records(
    forecasts: List[ForecastResult],
    period_index: int = 1,
    quantile_mode: str = "P50",
    default_sla_days: Optional[float] = None,
    default_service_level: float = 0.95,
) -> List[DemandRecord]:
    """
    Convert a collection of SKU-Market forecasts into DemandRecords for a specific period.

    Parameters
    ----------
    forecasts : List[ForecastResult]
        Probabilistic forecast outputs.
    period_index : int
        Which future horizon period to extract (1-based).
    quantile_mode : str
        "MEAN", "P50", "P10", or "P90". Determines which quantity is fed into `quantity`.
    """
    records: List[DemandRecord] = []

    for fc in forecasts:
        # Find the target period point
        matching_pts = [p for p in fc.horizon_points if p.period == period_index]
        if not matching_pts:
            continue
        pt = matching_pts[0]

        q_mode = quantile_mode.upper()
        if q_mode == "P10":
            qty = pt.p10
        elif q_mode == "P90":
            qty = pt.p90
        elif q_mode == "MEAN":
            qty = pt.mean
        else:
            qty = pt.p50

        # Create DemandRecord matching CanonicalNetwork schema
        rec = DemandRecord(
            market_id=fc.market_id,
            product_id=fc.product_id,
            period=period_index,
            quantity=float(round(qty, 4)),
            std_dev=float(round(pt.std_dev, 4)),
            sla_days=default_sla_days,
            service_level=default_service_level,
            priority=1,
        )
        records.append(rec)

    return records


def update_network_with_forecast(
    network: CanonicalNetwork,
    forecasts: List[ForecastResult],
    period_index: int = 1,
    quantile_mode: str = "P50",
) -> CanonicalNetwork:
    """
    Generate an updated CanonicalNetwork where demand records are replaced
    by the forecasted quantities and volatilities.
    """
    new_demands = forecast_to_demand_records(
        forecasts=forecasts,
        period_index=period_index,
        quantile_mode=quantile_mode,
    )

    # Build index of existing demands to preserve specific SLAs if present
    existing_meta = {
        (d.market_id, d.product_id): (d.sla_days, d.service_level, d.priority)
        for d in network.demands
    }

    merged_demands: List[DemandRecord] = []
    for d in new_demands:
        key = (d.market_id, d.product_id)
        if key in existing_meta:
            sla, s_lvl, prio = existing_meta[key]
            merged_demands.append(
                DemandRecord(
                    market_id=d.market_id,
                    product_id=d.product_id,
                    period=d.period,
                    quantity=d.quantity,
                    std_dev=d.std_dev,
                    sla_days=sla,
                    service_level=s_lvl,
                    priority=prio,
                )
            )
        else:
            merged_demands.append(d)

    # Return updated network model
    return network.model_copy(update={"demands": merged_demands})


def generate_scenario_networks(
    network: CanonicalNetwork,
    forecasts: List[ForecastResult],
    period_index: int = 1,
) -> Dict[str, CanonicalNetwork]:
    """
    Generate P10 (conservative), P50 (expected), and P90 (surge) CanonicalNetwork
    variants for scenario planning and robust MILP solving.
    """
    return {
        "p10_conservative": update_network_with_forecast(network, forecasts, period_index, "P10"),
        "p50_expected": update_network_with_forecast(network, forecasts, period_index, "P50"),
        "p90_surge": update_network_with_forecast(network, forecasts, period_index, "P90"),
    }
