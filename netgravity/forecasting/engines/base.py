"""
NetGravity — Abstract Base Forecaster
=====================================
Interface definition for all forecasting algorithms in NetGravity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from netgravity.forecasting.schemas import (
    DemandTimeSeries,
    ForecastResult,
)


class BaseForecaster(ABC):
    """
    Abstract base class that all forecasting model implementations must adhere to.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the forecasting engine."""
        pass

    @abstractmethod
    def fit_predict(
        self,
        time_series: DemandTimeSeries,
        horizon: int = 1,
    ) -> ForecastResult:
        """
        Fit the model on historical observations and generate a probabilistic forecast
        for the given horizon.

        Parameters
        ----------
        time_series : DemandTimeSeries
            Historical demand observations.
        horizon : int
            Number of future planning periods to forecast.

        Returns
        -------
        ForecastResult
            Probabilistic predictions (mean, std_dev, p10, p50, p90) for each period.
        """
        pass
