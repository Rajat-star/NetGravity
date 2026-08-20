"""
Tests for AI Data Sanitizer & Anomaly Detector
"""

import pytest
from netgravity.ingestion.ai.client import LLMClient
from netgravity.ingestion.ai.structured_sanitizer import sanitize_structured_records
from netgravity.ingestion.config import IngestionConfig
from netgravity.schemas.network import (
    DemandRecord,
    FacilityRecord,
    FacilityStatus,
    LaneRecord,
    NodeRole,
    ProductRecord,
    TransportMode,
)


def test_missing_geolocation_imputation():
    cfg = IngestionConfig(llm_api_key="")
    client = LLMClient(cfg)

    facility_missing_coords = FacilityRecord(
        id="DC_MUMBAI_NEW",
        name="Mumbai New DC",
        role=NodeRole.DC,
        status=FacilityStatus.EXISTING,
        latitude=0.0,
        longitude=0.0,
    )

    result = sanitize_structured_records(
        facilities=[facility_missing_coords],
        products=[],
        demands=[],
        lanes=[],
        config=cfg,
        client=client,
    )

    assert result.imputations_count == 1
    assert result.facilities[0].latitude == 19.0760
    assert result.facilities[0].longitude == 72.8777


def test_outlier_freight_rate_detection():
    cfg = IngestionConfig(llm_api_key="")
    client = LLMClient(cfg)

    lane_normal_1 = LaneRecord(origin_id="PUNE", destination_id="MUMBAI", rate_per_unit=15.0)
    lane_normal_2 = LaneRecord(origin_id="PUNE", destination_id="DELHI", rate_per_unit=25.0)
    lane_outlier = LaneRecord(origin_id="PUNE", destination_id="KOLKATA", rate_per_unit=2500.0)

    result = sanitize_structured_records(
        facilities=[],
        products=[],
        demands=[],
        lanes=[lane_normal_1, lane_normal_2, lane_outlier],
        config=cfg,
        client=client,
    )

    assert result.outliers_count == 1
    assert any(i.code == "R-019" for i in result.issues)


def test_hazmat_air_compliance_check():
    cfg = IngestionConfig(llm_api_key="")
    client = LLMClient(cfg)

    hazmat_sku = ProductRecord(
        id="SKU_HAZMAT",
        name="Lithium Ion Battery Pack",
        category="ELECTRONICS",
        is_hazmat=True,
    )

    air_lane = LaneRecord(
        origin_id="MUMBAI",
        destination_id="DELHI",
        mode=TransportMode.AIR,
        rate_per_unit=100.0,
        eligible_product_ids=["SKU_HAZMAT"],
    )

    result = sanitize_structured_records(
        facilities=[],
        products=[hazmat_sku],
        demands=[],
        lanes=[air_lane],
        config=cfg,
        client=client,
    )

    assert any(i.code == "R-020" for i in result.issues)
