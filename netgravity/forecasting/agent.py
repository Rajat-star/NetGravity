"""
NetGravity — AI Forecasting Agent
=================================
Main orchestration agent for time-series forecasting, external signal synthesis,
and seamless integration with the NetGravity MILP optimization engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from netgravity.forecasting.characterizer import characterize_series, compute_demand_metrics
from netgravity.forecasting.engines.auto_selector import AutoModelSelector
from netgravity.forecasting.schemas import (
    DemandPoint,
    DemandTimeSeries,
    ExternalSignalModifier,
    ForecastResult,
)
from netgravity.forecasting.signals.fuser import ExternalSignalFuser
from netgravity.forecasting.bridge.milp_bridge import (
    forecast_to_demand_records,
    generate_scenario_networks,
    update_network_with_forecast,
)
from netgravity.schemas.network import CanonicalNetwork, DemandRecord

logger = logging.getLogger(__name__)


class ForecastingAgent:
    """
    Intelligent forecasting agent coordinating multi-model predictions,
    external signal modulation, and MILP solver network updates.
    """

    def __init__(
        self,
        llm_api_key: Optional[str] = None,
    ) -> None:
        self.selector = AutoModelSelector()
        self.signal_fuser = ExternalSignalFuser(api_key=llm_api_key)

    def forecast_series(
        self,
        series: DemandTimeSeries,
        horizon: int = 1,
        external_signal_text: Optional[str] = None,
    ) -> ForecastResult:
        """
        Generate probabilistic forecast for a single SKU time series.
        """
        # Step 1: Base numerical forecast
        base_result = self.selector.fit_predict(series, horizon=horizon)

        # Step 2: Apply external signal if provided
        if external_signal_text and external_signal_text.strip():
            modifier = self.signal_fuser.extract_modifier_from_text(external_signal_text)
            final_result = self.signal_fuser.apply_modifier(base_result, modifier)
            return final_result

        return base_result

    def forecast_dataset(
        self,
        series_list: List[DemandTimeSeries],
        horizon: int = 1,
        external_signal_text: Optional[str] = None,
    ) -> List[ForecastResult]:
        """
        Batch forecast across multiple SKU-Market time series.
        """
        results: List[ForecastResult] = []
        
        # Pre-extract signal modifier once per batch to minimize token consumption
        modifier = None
        if external_signal_text and external_signal_text.strip():
            modifier = self.signal_fuser.extract_modifier_from_text(external_signal_text)

        for s in series_list:
            base_res = self.selector.fit_predict(s, horizon=horizon)
            if modifier is not None and modifier.event_type != "baseline":
                res = self.signal_fuser.apply_modifier(base_res, modifier)
            else:
                res = base_res
            results.append(res)

        return results

    def forecast_from_dataframe(
        self,
        df: pd.DataFrame,
        market_col: str = "market_id",
        product_col: str = "product_id",
        period_col: str = "period",
        quantity_col: str = "quantity",
        horizon: int = 1,
        external_signal_text: Optional[str] = None,
    ) -> List[ForecastResult]:
        """
        Parse raw DataFrame from Extraction Agent and generate forecasts.
        """
        series_list: List[DemandTimeSeries] = []

        grouped = df.groupby([market_col, product_col])
        for (m_id, p_id), group in grouped:
            sorted_group = group.sort_values(period_col)
            points = [
                DemandPoint(
                    period=int(row[period_col]),
                    quantity=float(row[quantity_col]),
                )
                for _, row in sorted_group.iterrows()
            ]
            series = DemandTimeSeries(
                market_id=str(m_id),
                product_id=str(p_id),
                history=points,
            )
            series_list.append(series)

        return self.forecast_dataset(
            series_list,
            horizon=horizon,
            external_signal_text=external_signal_text,
        )

    def update_network_demands(
        self,
        network: CanonicalNetwork,
        forecasts: List[ForecastResult],
        period_index: int = 1,
        quantile_mode: str = "P50",
    ) -> CanonicalNetwork:
        """Update CanonicalNetwork demand records with forecasted values."""
        return update_network_with_forecast(network, forecasts, period_index, quantile_mode)

    def generate_scenario_variations(
        self,
        network: CanonicalNetwork,
        forecasts: List[ForecastResult],
        period_index: int = 1,
    ) -> Dict[str, CanonicalNetwork]:
        """Produce P10, P50, and P90 scenario networks for robust optimization."""
        return generate_scenario_networks(network, forecasts, period_index)
