"""
NetGravity — External Signal & Scenario Fuser
=============================================
Fuses unstructured external signals (Google Search trends, disruption alerts,
supplier strikes, contractual terms) with baseline time-series forecasts.

Uses a surgical, single-batch prompt to minimize AI token costs, with a deterministic
semantic keyword rule-engine fallback when operating offline.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from netgravity.forecasting.schemas import (
    ExternalSignalModifier,
    ForecastPoint,
    ForecastResult,
)

logger = logging.getLogger(__name__)


# Deterministic semantic rules for offline / zero-token fallback
KEYWORD_RULES = [
    (r"\b(surge|festival|diwali|holiday|boom|promo|peak)\b", 1.25, 1.30, 0.0, "Demand surge detected from seasonal or promo signals"),
    (r"\b(strike|port congestion|disruption|delay|blockage)\b", 0.90, 1.50, 4.0, "Supply disruption and transit lead time escalation"),
    (r"\b(monsoon|flood|storm|cyclone|weather warning)\b", 0.85, 1.40, 2.5, "Severe weather logistics constraint and volatility increase"),
    (r"\b(recession|downturn|slump|drop|decline)\b", 0.80, 1.10, 0.0, "Macroeconomic demand contraction"),
    (r"\b(expansion|new plant|new store|opening)\b", 1.20, 1.15, -1.0, "Network expansion and capacity increment"),
]


class ExternalSignalFuser:
    """
    Synthesizes external signals into bounded numerical modifiers.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("NETGRAVITY_LLM_API_KEY")

    def extract_modifier_from_text(
        self,
        signal_text: str,
        source: str = "external_search",
    ) -> ExternalSignalModifier:
        """
        Extract numerical impact multipliers from text using LLM or rule-based fallback.
        """
        if not signal_text or not signal_text.strip():
            return ExternalSignalModifier(source=source, event_type="none", reasoning="No external signals provided")

        # If LLM API key is present and anthropic/client installed, we can invoke LLM
        if self.api_key and len(self.api_key) > 5:
            try:
                import anthropic  # type: ignore
                client = anthropic.Anthropic(api_key=self.api_key)
                prompt = (
                    "You are a supply chain risk analyst. Analyze the following external signal text and "
                    "return ONLY a raw JSON object with keys: "
                    "event_type (str), demand_multiplier (float between 0.5 and 2.0), "
                    "std_dev_multiplier (float between 0.8 and 2.5), lead_time_delta_days (float), "
                    "confidence (float 0 to 1), reasoning (str max 30 words).\n\n"
                    f"Signal Text: {signal_text}\n\nJSON:"
                )
                resp = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=200,
                    temperature=0.0,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_json = resp.content[0].text
                data = json.loads(raw_json.strip())
                return ExternalSignalModifier(
                    source=source,
                    event_type=data.get("event_type", "market_event"),
                    demand_multiplier=float(data.get("demand_multiplier", 1.0)),
                    std_dev_multiplier=float(data.get("std_dev_multiplier", 1.0)),
                    lead_time_delta_days=float(data.get("lead_time_delta_days", 0.0)),
                    confidence=float(data.get("confidence", 0.85)),
                    reasoning=data.get("reasoning", "LLM signal synthesis"),
                )
            except Exception as e:
                logger.warning(f"LLM signal extraction failed, falling back to rule engine: {e}")

        # Deterministic rule-based extraction ($0 token cost)
        text_lower = signal_text.lower()
        matched_rules = []
        d_mult = 1.0
        sd_mult = 1.0
        lt_delta = 0.0
        reasons = []

        for pattern, d_m, sd_m, lt_d, reason in KEYWORD_RULES:
            if re.search(pattern, text_lower):
                d_mult *= d_m
                sd_mult *= sd_m
                lt_delta += lt_d
                reasons.append(reason)

        # Bounding constraints
        d_mult = max(0.5, min(2.0, d_mult))
        sd_mult = max(0.8, min(3.0, sd_mult))

        if reasons:
            return ExternalSignalModifier(
                source=source,
                event_type="semantic_event",
                demand_multiplier=float(round(d_mult, 3)),
                std_dev_multiplier=float(round(sd_mult, 3)),
                lead_time_delta_days=float(round(lt_delta, 1)),
                confidence=0.80,
                reasoning="; ".join(reasons),
            )

        return ExternalSignalModifier(
            source=source,
            event_type="baseline",
            demand_multiplier=1.0,
            std_dev_multiplier=1.0,
            lead_time_delta_days=0.0,
            confidence=0.90,
            reasoning="Normal operating conditions",
        )

    def apply_modifier(
        self,
        forecast: ForecastResult,
        modifier: ExternalSignalModifier,
    ) -> ForecastResult:
        """
        Apply signal multiplier to forecast points.
        """
        adjusted_points: List[ForecastPoint] = []

        for pt in forecast.horizon_points:
            adj_mean = max(0.0, pt.mean * modifier.demand_multiplier)
            adj_std = max(0.0, pt.std_dev * modifier.std_dev_multiplier)
            adj_p10 = max(0.0, adj_mean - 1.282 * adj_std)
            adj_p50 = adj_mean
            adj_p90 = adj_mean + 1.282 * adj_std

            adjusted_points.append(
                ForecastPoint(
                    period=pt.period,
                    mean=adj_mean,
                    std_dev=adj_std,
                    p10=adj_p10,
                    p50=adj_p50,
                    p90=adj_p90,
                )
            )

        return ForecastResult(
            market_id=forecast.market_id,
            product_id=forecast.product_id,
            engine_name=f"{forecast.engine_name}+SignalMod",
            pattern=forecast.pattern,
            metrics=forecast.metrics,
            horizon_points=adjusted_points,
            signal_applied=modifier,
            confidence_score=forecast.confidence_score * modifier.confidence,
            metadata=forecast.metadata,
        )
