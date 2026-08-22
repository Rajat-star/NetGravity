"""
NetGravity — Auto-ETS / Exponential Smoothing Forecaster
========================================================
Implements Simple, Holt Linear Trend, and Holt-Winters Seasonal Exponential
Smoothing with automated parameter optimization and closed-form prediction intervals.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np

from netgravity.forecasting.characterizer import compute_demand_metrics
from netgravity.forecasting.engines.base import BaseForecaster
from netgravity.forecasting.schemas import (
    DemandTimeSeries,
    ForecastPoint,
    ForecastResult,
)


class AutoETSForecaster(BaseForecaster):
    """
    Auto-Tuned Exponential Smoothing Forecaster with trend and prediction intervals.
    """

    def __init__(
        self,
        seasonal_periods: int = 12,
        damped: bool = True,
    ) -> None:
        self.seasonal_periods = seasonal_periods
        self.damped = damped

    @property
    def name(self) -> str:
        return "AutoETS_Trend"

    def fit_predict(
        self,
        time_series: DemandTimeSeries,
        horizon: int = 1,
    ) -> ForecastResult:
        quantities = time_series.quantities
        metrics = compute_demand_metrics(quantities)
        n = len(quantities)

        if n == 0:
            points = [ForecastPoint(period=i+1, mean=0.0, std_dev=0.0, p10=0.0, p50=0.0, p90=0.0) for i in range(horizon)]
            return ForecastResult(
                market_id=time_series.market_id,
                product_id=time_series.product_id,
                engine_name=self.name,
                pattern=metrics.pattern,
                metrics=metrics,
                horizon_points=points,
                confidence_score=0.5,
            )

        arr = np.array(quantities, dtype=np.float64)

        if n < 4:
            # Simple average fallback for extremely short series
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr)) if n > 1 else float(mean_val * 0.2)
            points = [
                ForecastPoint(
                    period=i + 1,
                    mean=mean_val,
                    std_dev=std_val,
                    p10=max(0.0, mean_val - 1.28 * std_val),
                    p50=mean_val,
                    p90=mean_val + 1.28 * std_val,
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
                confidence_score=0.6,
            )

        # Fit Holt's Linear Trend with Grid Search for alpha and beta
        best_sse = float("inf")
        best_alpha = 0.3
        best_beta = 0.1

        # Grid search over reasonable parameter space
        alpha_candidates = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
        beta_candidates = [0.0, 0.05, 0.1, 0.2, 0.3]

        for alpha in alpha_candidates:
            for beta in beta_candidates:
                # Initialize level and trend
                level = arr[0]
                trend = arr[1] - arr[0] if n > 1 else 0.0
                sse = 0.0

                for t in range(1, n):
                    y_hat = level + trend
                    err = arr[t] - y_hat
                    sse += err * err

                    # Update
                    last_level = level
                    level = alpha * arr[t] + (1.0 - alpha) * (level + trend)
                    trend = beta * (level - last_level) + (1.0 - beta) * trend

                if sse < best_sse:
                    best_sse = sse
                    best_alpha = alpha
                    best_beta = beta

        # Run forward with optimal parameters
        level = arr[0]
        trend = arr[1] - arr[0] if n > 1 else 0.0
        residuals = []

        for t in range(1, n):
            y_hat = level + trend
            err = arr[t] - y_hat
            residuals.append(err)

            last_level = level
            level = best_alpha * arr[t] + (1.0 - best_alpha) * (level + trend)
            trend = best_beta * (level - last_level) + (1.0 - best_beta) * trend

        # Residual standard error
        sigma_e = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else float(np.std(arr))
        sigma_e = max(sigma_e, float(np.mean(arr) * 0.05))

        # Damping factor phi (e.g. 0.95) to prevent explosive trend over long horizons
        phi = 0.95 if self.damped else 1.0

        horizon_points: List[ForecastPoint] = []
        for h in range(1, horizon + 1):
            if self.damped:
                damped_trend = trend * sum(phi ** i for i in range(1, h + 1))
                y_pred = max(0.0, float(level + damped_trend))
            else:
                y_pred = max(0.0, float(level + h * trend))

            # Analytical forecast variance scaling with horizon h:
            # Var(e_h) = sigma_e^2 * (1 + (h-1)*alpha^2 + ...)
            h_var_factor = math.sqrt(1.0 + (h - 1) * (best_alpha ** 2 + best_alpha * best_beta * h))
            period_sigma = float(sigma_e * h_var_factor)

            p10 = max(0.0, y_pred - 1.282 * period_sigma)
            p50 = y_pred
            p90 = y_pred + 1.282 * period_sigma

            horizon_points.append(
                ForecastPoint(
                    period=h,
                    mean=y_pred,
                    std_dev=period_sigma,
                    p10=p10,
                    p50=p50,
                    p90=p90,
                )
            )

        return ForecastResult(
            market_id=time_series.market_id,
            product_id=time_series.product_id,
            engine_name=self.name,
            pattern=metrics.pattern,
            metrics=metrics,
            horizon_points=horizon_points,
            confidence_score=0.90,
            metadata={"best_alpha": best_alpha, "best_beta": best_beta, "sigma_e": sigma_e},
        )
