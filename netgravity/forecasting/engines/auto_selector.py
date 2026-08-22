"""
NetGravity — Automatic Forecasting Model Selector
=================================================
Automated intelligent routing that selects the best forecasting algorithm
based on the SKU's demand characterization (ADI vs CV²) and series length.
"""

from __future__ import annotations

from typing import Dict, Optional

from netgravity.forecasting.characterizer import compute_demand_metrics
from netgravity.forecasting.engines.base import BaseForecaster
from netgravity.forecasting.engines.ets_smoother import AutoETSForecaster
from netgravity.forecasting.engines.foundation_adapter import FoundationZeroShotForecaster
from netgravity.forecasting.engines.intermittent import IntermittentForecaster
from netgravity.forecasting.engines.quantile_regressor import QuantileRegressionForecaster
from netgravity.forecasting.schemas import (
    DemandPattern,
    DemandTimeSeries,
    ForecastResult,
)


class AutoModelSelector(BaseForecaster):
    """
    Meta-Forecaster that automatically classifies demand and invokes the optimal engine.
    """

    def __init__(self) -> None:
        self.intermittent_engine = IntermittentForecaster(method="SBA")
        self.quantile_engine = QuantileRegressionForecaster()
        self.ets_engine = AutoETSForecaster()
        self.foundation_engine = FoundationZeroShotForecaster()

    @property
    def name(self) -> str:
        return "AutoModel_Selector"

    def select_engine(self, time_series: DemandTimeSeries) -> BaseForecaster:
        """
        Determine the optimal engine based on demand pattern and historical depth.
        """
        metrics = compute_demand_metrics(time_series.quantities)

        if metrics.pattern == DemandPattern.COLD_START:
            return self.foundation_engine
        elif metrics.pattern in (DemandPattern.INTERMITTENT, DemandPattern.LUMPY):
            return self.intermittent_engine
        elif metrics.pattern == DemandPattern.ERRATIC:
            return self.quantile_engine
        else:
            # SMOOTH demand: use Quantile regressor if enough history, otherwise AutoETS
            if metrics.total_periods >= 12:
                return self.quantile_engine
            return self.ets_engine

    def fit_predict(
        self,
        time_series: DemandTimeSeries,
        horizon: int = 1,
    ) -> ForecastResult:
        """Auto-select optimal model and execute forecast."""
        engine = self.select_engine(time_series)
        return engine.fit_predict(time_series, horizon=horizon)
