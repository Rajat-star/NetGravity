"""
NetGravity — Intermittent & Lumpy Demand Forecasting Engine
===========================================================
Implements Croston's Method (1972) and the Syntetos-Boylan Approximation (SBA, 2005)
for sporadic and spare-parts demand.

Prevents the severe over-forecasting and inventory bloat that occurs when standard
ARIMA or Neural Net models are applied to sparse or zero-inflated series.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np

from netgravity.forecasting.characterizer import compute_demand_metrics
from netgravity.forecasting.engines.base import BaseForecaster
from netgravity.forecasting.schemas import (
    DemandPattern,
    DemandTimeSeries,
    ForecastPoint,
    ForecastResult,
)


class IntermittentForecaster(BaseForecaster):
    """
    Syntetos-Boylan (SBA) and Croston Forecaster for intermittent / lumpy demand.
    """

    def __init__(
        self,
        method: str = "SBA",
        alpha: float = 0.15,
    ) -> None:
        """
        Parameters
        ----------
        method : str
            "SBA" (Syntetos-Boylan Approximation, recommended) or "CROSTON".
        alpha : float
            Exponential smoothing parameter in (0, 1). Default 0.15.
        """
        self.method = method.upper()
        self.alpha = min(max(alpha, 0.01), 0.99)

    @property
    def name(self) -> str:
        return f"{self.method}_Intermittent"

    def fit_predict(
        self,
        time_series: DemandTimeSeries,
        horizon: int = 1,
    ) -> ForecastResult:
        """
        Compute Croston / SBA demand rate and probabilistic quantiles.
        """
        quantities = time_series.quantities
        metrics = compute_demand_metrics(quantities)

        if not quantities or metrics.non_zero_periods == 0:
            # Series is entirely zero
            points = [
                ForecastPoint(
                    period=i + 1,
                    mean=0.0,
                    std_dev=0.0,
                    p10=0.0,
                    p50=0.0,
                    p90=0.0,
                )
                for i in range(horizon)
            ]
            return ForecastResult(
                market_id=time_series.market_id,
                product_id=time_series.product_id,
                engine_name=self.name,
                pattern=metrics.pattern,
                metrics=metrics,
                horizon_points=points,
                confidence_score=0.9,
            )

        # Initialize Croston state
        # Find first non-zero demand
        first_nz_idx = next(i for i, q in enumerate(quantities) if q > 0)
        z = float(quantities[first_nz_idx])  # Demand size
        p = float(first_nz_idx + 1)         # Inter-arrival interval
        q = 1                               # Elapsed periods counter

        for t in range(first_nz_idx + 1, len(quantities)):
            d = float(quantities[t])
            if d > 0:
                z = self.alpha * d + (1.0 - self.alpha) * z
                p = self.alpha * q + (1.0 - self.alpha) * p
                q = 1
            else:
                q += 1

        # Prevent division by zero
        p = max(p, 1.0)
        z = max(z, 0.0)

        # Point forecast rate per period
        if self.method == "SBA":
            # Syntetos-Boylan deflates Croston's positive bias by factor (1 - alpha / 2)
            sba_factor = max(0.0, 1.0 - (self.alpha / 2.0))
            rate = sba_factor * (z / p)
        else:
            rate = z / p

        # Calculate empirical dispersion / standard deviation
        arr = np.array(quantities, dtype=np.float64)
        std_dev = float(np.std(arr, ddof=1)) if len(arr) > 1 else float(rate * 0.5)

        # Zero-inflated Quantiles
        # Probability of zero demand in any period is ~ (1 - 1/p)
        prob_zero = max(0.0, min(1.0, 1.0 - (1.0 / p)))
        
        # P10: If zero probability is high, P10 is strictly 0
        p10 = 0.0 if prob_zero >= 0.1 else max(0.0, rate - 1.28 * std_dev)
        # P50: Median demand
        p50 = 0.0 if prob_zero >= 0.5 else max(0.0, rate)
        # P90: Upper bound for when demand DOES occur
        # If demand occurs, expected size is z with variance; P90 captures surge
        p90 = max(rate, z + 1.28 * (std_dev if std_dev > 0 else z * 0.3))

        horizon_points = [
            ForecastPoint(
                period=i + 1,
                mean=float(rate),
                std_dev=float(std_dev),
                p10=float(p10),
                p50=float(p50),
                p90=float(p90),
            )
            for i in range(horizon)
        ]

        return ForecastResult(
            market_id=time_series.market_id,
            product_id=time_series.product_id,
            engine_name=self.name,
            pattern=metrics.pattern,
            metrics=metrics,
            horizon_points=horizon_points,
            confidence_score=0.85,
        )
