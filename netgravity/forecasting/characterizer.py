"""
NetGravity — Demand Pattern Characterizer
=========================================
Implements the industry-standard Syntetos-Boylan ADI vs CV² demand categorization
matrix (Syntetos, Babai & Gardner, 2005).

Automatically characterizes any time-series into:
  - SMOOTH:       Continuous regular demand (ADI < 1.32, CV² < 0.49)
  - INTERMITTENT: Sporadic constant-sized demand (ADI >= 1.32, CV² < 0.49)
  - ERRATIC:      Continuous volatile demand (ADI < 1.32, CV² >= 0.49)
  - LUMPY:        Sporadic volatile demand (ADI >= 1.32, CV² >= 0.49)
  - COLD_START:   Sparse history (< 8 observations)
"""

from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np

from netgravity.forecasting.schemas import (
    CharacterizationMetrics,
    DemandPattern,
    DemandTimeSeries,
)

# Standard Syntetos-Boylan / Johnston-Boylan cutoff thresholds
ADI_CUTOFF: float = 1.32
CV2_CUTOFF: float = 0.49
MIN_SERIES_LENGTH: int = 8


def compute_demand_metrics(quantities: Sequence[float]) -> CharacterizationMetrics:
    """
    Calculate mathematical demand metrics: ADI, CV², and classification.

    Parameters
    ----------
    quantities : Sequence[float]
        Ordered sequence of historical demand quantities.

    Returns
    -------
    CharacterizationMetrics
        Calculated metrics including pattern classification.
    """
    arr = np.array(quantities, dtype=np.float64)
    total_periods = len(arr)

    if total_periods < MIN_SERIES_LENGTH:
        # Insufficient data points for robust statistical classification
        non_zero = arr[arr > 0]
        non_zero_count = len(non_zero)
        zero_ratio = float((total_periods - non_zero_count) / max(1, total_periods))
        return CharacterizationMetrics(
            adi=float(total_periods / max(1, non_zero_count)),
            cv2=0.0 if non_zero_count <= 1 else float(np.var(non_zero, ddof=1) / max(1e-6, np.mean(non_zero)**2)),
            non_zero_periods=non_zero_count,
            total_periods=total_periods,
            zero_ratio=zero_ratio,
            pattern=DemandPattern.COLD_START,
        )

    non_zero = arr[arr > 0]
    non_zero_count = len(non_zero)
    zero_ratio = float((total_periods - non_zero_count) / total_periods)

    if non_zero_count == 0:
        # Pure all-zero series
        return CharacterizationMetrics(
            adi=float(total_periods),
            cv2=0.0,
            non_zero_periods=0,
            total_periods=total_periods,
            zero_ratio=1.0,
            pattern=DemandPattern.INTERMITTENT,
        )

    # ADI = Total periods / Number of non-zero demand periods
    adi = float(total_periods / non_zero_count)

    # CV² = (Standard Deviation / Mean)² of non-zero demands
    mean_nz = float(np.mean(non_zero))
    if non_zero_count > 1 and mean_nz > 1e-9:
        var_nz = float(np.var(non_zero, ddof=1))
        cv2 = float(var_nz / (mean_nz ** 2))
    else:
        cv2 = 0.0

    # Categorization Matrix
    if adi < ADI_CUTOFF:
        if cv2 < CV2_CUTOFF:
            pattern = DemandPattern.SMOOTH
        else:
            pattern = DemandPattern.ERRATIC
    else:
        if cv2 < CV2_CUTOFF:
            pattern = DemandPattern.INTERMITTENT
        else:
            pattern = DemandPattern.LUMPY

    return CharacterizationMetrics(
        adi=adi,
        cv2=cv2,
        non_zero_periods=non_zero_count,
        total_periods=total_periods,
        zero_ratio=zero_ratio,
        pattern=pattern,
    )


def characterize_series(series: DemandTimeSeries) -> CharacterizationMetrics:
    """Convenience helper to characterize a DemandTimeSeries instance."""
    return compute_demand_metrics(series.quantities)
