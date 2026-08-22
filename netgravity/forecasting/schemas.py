"""
NetGravity — Forecasting Data Schemas
=====================================
Typed Pydantic data contracts for time-series inputs, demand classification,
probabilistic forecasts, and external signal modulation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class DemandPattern(str, Enum):
    """
    Standard Syntetos-Boylan demand classification categories plus cold-start.
    """
    SMOOTH       = "SMOOTH"        # Low ADI, Low CV²: High predictability, continuous demand
    INTERMITTENT = "INTERMITTENT"  # High ADI, Low CV²: Sporadic demand, constant sizing
    ERRATIC      = "ERRATIC"       # Low ADI, High CV²: Continuous demand, volatile sizing
    LUMPY        = "LUMPY"         # High ADI, High CV²: Sporadic demand, volatile sizing
    COLD_START   = "COLD_START"    # Insufficient historical periods (< 8 data points)


class DemandPoint(BaseModel):
    """A single historical demand observation in a planning period."""
    period: int = Field(..., description="1-indexed or sequential period number")
    quantity: float = Field(..., ge=0.0, description="Observed demand units in the period")
    timestamp: Optional[str] = Field(None, description="ISO timestamp or date string if available")


class DemandTimeSeries(BaseModel):
    """
    Time-series demand history for a specific market-product (SKU) pair.
    """
    market_id: str = Field(..., description="Destination market / customer node ID")
    product_id: str = Field(..., description="Product / SKU ID")
    history: List[DemandPoint] = Field(default_factory=list, description="Sequential historical observations")
    frequency: str = Field("MONTH", description="Observation frequency (DAY, WEEK, MONTH, QUARTER)")
    sla_days: Optional[float] = Field(None, description="Service level agreement lead time threshold")
    service_level: float = Field(0.95, ge=0.0, le=1.0, description="Target cycle service level SLA")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary SKU/Market metadata")

    @property
    def quantities(self) -> List[float]:
        """Return raw historical quantities in sequence."""
        return [p.quantity for p in sorted(self.history, key=lambda x: x.period)]

    @property
    def total_periods(self) -> int:
        return len(self.history)


class CharacterizationMetrics(BaseModel):
    """
    Mathematical metrics determining demand classification (ADI vs CV²).
    """
    adi: float = Field(..., description="Average Demand Interval (average periods between non-zero demand)")
    cv2: float = Field(..., description="Squared Coefficient of Variation of non-zero demand quantities")
    non_zero_periods: int = Field(..., description="Count of periods with positive demand")
    total_periods: int = Field(..., description="Total periods analyzed")
    zero_ratio: float = Field(..., description="Fraction of zero-demand periods")
    pattern: DemandPattern = Field(..., description="Classified demand pattern")


class ForecastPoint(BaseModel):
    """Probabilistic forecast for a future horizon period."""
    period: int = Field(..., description="Future planning period index (1-based from start of forecast)")
    mean: float = Field(..., ge=0.0, description="Expected / point demand forecast (E[D])")
    std_dev: float = Field(0.0, ge=0.0, description="Forecast standard deviation / volatility (σ_D)")
    p10: float = Field(..., ge=0.0, description="10th percentile forecast (conservative lower bound)")
    p50: float = Field(..., ge=0.0, description="50th percentile forecast (median expected demand)")
    p90: float = Field(..., ge=0.0, description="90th percentile forecast (surge upper bound)")


class ExternalSignalModifier(BaseModel):
    """
    Structured modifier extracted from external news, contracts, or search signals.
    """
    source: str = Field("external_search", description="Source of the signal (news, search, contract, macro)")
    event_type: str = Field("market_trend", description="Disruption, surge, regulatory, or contract event")
    demand_multiplier: float = Field(1.0, ge=0.1, le=5.0, description="Multiplicative modifier on baseline demand")
    std_dev_multiplier: float = Field(1.0, ge=0.5, le=5.0, description="Volatility scale factor")
    lead_time_delta_days: float = Field(0.0, description="Expected change in supplier/transit lead time")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of the signal extraction")
    reasoning: str = Field("", description="Human/LLM rationale for the adjustment")


class ForecastResult(BaseModel):
    """
    Complete probabilistic forecast output for an SKU-Market pair across a horizon.
    """
    market_id: str
    product_id: str
    engine_name: str = Field(..., description="Name of the forecasting algorithm used")
    pattern: DemandPattern = Field(..., description="Underlying demand pattern identified")
    metrics: Optional[CharacterizationMetrics] = None
    horizon_points: List[ForecastPoint] = Field(default_factory=list)
    signal_applied: Optional[ExternalSignalModifier] = None
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_expected_demand(self) -> float:
        """Sum of mean forecasted demand over the planning horizon."""
        return sum(pt.mean for pt in self.horizon_points)

    @property
    def average_period_volatility(self) -> float:
        """Average standard deviation across horizon periods."""
        if not self.horizon_points:
            return 0.0
        return sum(pt.std_dev for pt in self.horizon_points) / len(self.horizon_points)
