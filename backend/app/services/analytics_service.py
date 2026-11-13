from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import logging
from pathlib import Path
from typing import Any
import uuid

import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.farm import Farm
from app.models.modules import (
    ChatSession,
    CropPrediction,
    CropRecommendation,
    DiseaseDetection,
    FertilizerRecommendation,
    IrrigationRecommendation,
)
from app.models.user import User
from app.schemas.analytics import (
    AnnualTrendItem,
    CorrelationItem,
    CropActivityBreakdown,
    CropDistributionItem,
    DailyActivityPoint,
    DatasetAnalyticsFilter,
    DatasetAnalyticsResponse,
    DiseaseActivityBreakdown,
    FarmActivityBreakdown,
    FertilizerActivityBreakdown,
    ModuleActivitySummary,
    StateProductionItem,
    UserOperationalAnalyticsResponse,
    YieldComparisonItem,
)
from ml.preprocessing.disease_features import parse_plantvillage_label

logger = logging.getLogger("terraqora.analytics")

ROOT_DIR = Path(__file__).resolve().parents[3]
CROP_YIELD_CSV = ROOT_DIR / "ml" / "datasets" / "raw" / "crop_yield.csv"


def get_user_operational_analytics(
    db: Session,
    current_user: User,
    *,
    range_days: int = 30,
    farm_id: uuid.UUID | None = None,
) -> UserOperationalAnalyticsResponse:
    """Computes real-time, user-isolated operational farm intelligence from authenticated DB records."""
    target_farm: Farm | None = None
    if farm_id is not None:
        target_farm = db.get(Farm, farm_id)
        if target_farm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected farm plot was not found.",
            )
        if target_farm.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to view analytics for this farm plot.",
            )

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=max(1, min(range_days, 3650)))

    # Fetch user's registered farms
    user_farms = db.scalars(
        select(Farm)
        .where(Farm.user_id == current_user.id)
        .order_by(Farm.created_at.asc())
    ).all()
    active_farms_count = len(user_farms)
    total_hectares = sum(float(f.area_hectares or 0.0) for f in user_farms)

    # Base filter helpers
    def apply_filters(query: Any, model: Any) -> Any:
        q = query.where(model.user_id == current_user.id, model.created_at >= cutoff)
        if farm_id is not None:
            q = q.where(model.farm_id == farm_id)
        return q

    # 1. Fetch module activity records
    crop_preds = db.scalars(apply_filters(select(CropPrediction), CropPrediction)).all()
    crop_recs = db.scalars(apply_filters(select(CropRecommendation), CropRecommendation)).all()
    fert_recs = db.scalars(apply_filters(select(FertilizerRecommendation), FertilizerRecommendation)).all()
    disease_scans = db.scalars(apply_filters(select(DiseaseDetection), DiseaseDetection)).all()
    irrigation_recs = db.scalars(apply_filters(select(IrrigationRecommendation), IrrigationRecommendation)).all()
    chat_sessions = db.scalars(apply_filters(select(ChatSession), ChatSession)).all()

    summary = ModuleActivitySummary(
        yield_predictions=len(crop_preds),
        crop_recommendations=len(crop_recs),
        fertilizer_recommendations=len(fert_recs),
        disease_detections=len(disease_scans),
        irrigation_advisories=len(irrigation_recs),
        ai_chat_sessions=len(chat_sessions),
        total_activities=(
            len(crop_preds)
            + len(crop_recs)
            + len(fert_recs)
            + len(disease_scans)
            + len(irrigation_recs)
        ),
        active_farms_count=active_farms_count,
        total_hectares_managed=round(total_hectares, 2),
    )

    # 2. Build Daily Activity Timeline
    timeline_days = min(range_days, 90)
    start_day = (now_utc - timedelta(days=timeline_days - 1)).date()
    daily_map: dict[str, dict[str, int]] = {
        (start_day + timedelta(days=i)).strftime("%Y-%m-%d"): {
            "yield": 0,
            "crop_rec": 0,
            "fert": 0,
            "disease": 0,
            "irr": 0,
        }
        for i in range(timeline_days)
    }

    for p in crop_preds:
        d_str = p.created_at.strftime("%Y-%m-%d")
        if d_str in daily_map:
            daily_map[d_str]["yield"] += 1
    for cr in crop_recs:
        d_str = cr.created_at.strftime("%Y-%m-%d")
        if d_str in daily_map:
            daily_map[d_str]["crop_rec"] += 1
    for fr in fert_recs:
        d_str = fr.created_at.strftime("%Y-%m-%d")
        if d_str in daily_map:
            daily_map[d_str]["fert"] += 1
    for ds in disease_scans:
        d_str = ds.created_at.strftime("%Y-%m-%d")
        if d_str in daily_map:
            daily_map[d_str]["disease"] += 1
    for ir in irrigation_recs:
        d_str = ir.created_at.strftime("%Y-%m-%d")
        if d_str in daily_map:
            daily_map[d_str]["irr"] += 1

    timeline: list[DailyActivityPoint] = [
        DailyActivityPoint(
            date=d_key,
            yield_predictions=counts["yield"],
            crop_recommendations=counts["crop_rec"],
            fertilizer_recommendations=counts["fert"],
            disease_detections=counts["disease"],
            irrigation_advisories=counts["irr"],
            total=sum(counts.values()),
        )
        for d_key, counts in sorted(daily_map.items())
    ]

    # 3. Crop Distribution & Yield Analysis
    crop_stats: dict[str, list[float]] = defaultdict(list)
    crop_units: dict[str, str] = {}
    for p in crop_preds:
        crop_stats[p.crop].append(float(p.predicted_yield))
        crop_units[p.crop] = p.yield_unit
    for cr in crop_recs:
        if cr.recommended_crop not in crop_stats:
            crop_stats[cr.recommended_crop] = []

    top_crops: list[CropActivityBreakdown] = [
        CropActivityBreakdown(
            crop=crop_name,
            count=len(yield_list) or len([cr for cr in crop_recs if cr.recommended_crop == crop_name]),
            avg_yield=round(float(np.mean(yield_list)), 2) if yield_list else None,
            yield_unit=crop_units.get(crop_name, "tonnes/hectare"),
        )
        for crop_name, yield_list in sorted(
            crop_stats.items(),
            key=lambda kv: len(kv[1]),
            reverse=True,
        )[:8]
    ]

    # 4. Disease Findings Breakdown
    disease_groups: dict[str, list[DiseaseDetection]] = defaultdict(list)
    for ds in disease_scans:
        disease_groups[ds.predicted_label].append(ds)

    disease_findings: list[DiseaseActivityBreakdown] = []
    for label, group in sorted(disease_groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:8]:
        crop_name, disease_name, _ = parse_plantvillage_label(label)
        if "Uncertain" in label:
            disease_name = "Uncertain Screening"
            crop_name = group[0].crop_hint or crop_name
        disease_findings.append(
            DiseaseActivityBreakdown(
                label=label,
                crop_name=crop_name,
                disease_name=disease_name,
                count=len(group),
                uncertain_count=sum(1 for d in group if d.is_uncertain),
                avg_confidence=round(float(np.mean([d.confidence for d in group])), 3),
            )
        )

    # 5. Fertilizer Formulations Breakdown
    fert_counter = Counter(f.recommended_fertilizer for f in fert_recs)
    fertilizer_grades: list[FertilizerActivityBreakdown] = [
        FertilizerActivityBreakdown(recommended_fertilizer=k, count=v)
        for k, v in fert_counter.most_common(6)
    ]

    # 6. Farm-level Activity Breakdown
    farm_activity_counts: dict[uuid.UUID, int] = defaultdict(int)
    farm_latest_date: dict[uuid.UUID, datetime] = {}

    def track_farm(fid: uuid.UUID | None, ts: datetime) -> None:
        if fid is not None:
            farm_activity_counts[fid] += 1
            if fid not in farm_latest_date or ts > farm_latest_date[fid]:
                farm_latest_date[fid] = ts

    for p in crop_preds:
        track_farm(p.farm_id, p.created_at)
    for cr in crop_recs:
        track_farm(cr.farm_id, cr.created_at)
    for fr in fert_recs:
        track_farm(fr.farm_id, fr.created_at)
    for ds in disease_scans:
        track_farm(ds.farm_id, ds.created_at)
    for ir in irrigation_recs:
        track_farm(ir.farm_id, ir.created_at)

    farm_breakdown: list[FarmActivityBreakdown] = [
        FarmActivityBreakdown(
            farm_id=str(f.id),
            farm_name=f.name,
            state=f.state,
            area_hectares=float(f.area_hectares),
            total_activities=farm_activity_counts.get(f.id, 0),
            last_activity=farm_latest_date.get(f.id),
        )
        for f in user_farms
    ]

    return UserOperationalAnalyticsResponse(
        summary=summary,
        filter_range_days=range_days,
        filter_farm_id=target_farm.id if target_farm else None,
        filter_farm_name=target_farm.name if target_farm else None,
        timeline=timeline,
        top_crops=top_crops,
        disease_findings=disease_findings,
        fertilizer_grades=fertilizer_grades,
        farm_breakdown=farm_breakdown,
        source_mode="live_api",
    )


# --- Macro Dataset Analytics Engine ---

@lru_cache(maxsize=1)
def _load_raw_crop_yield_df() -> pd.DataFrame:
    if not CROP_YIELD_CSV.exists():
        raise FileNotFoundError(f"Missing dataset at {CROP_YIELD_CSV}")
    df = pd.read_csv(CROP_YIELD_CSV)
    df["Crop"] = df["Crop"].astype(str).str.strip()
    df["Season"] = df["Season"].astype(str).str.strip()
    df["State"] = df["State"].astype(str).str.strip()
    return df


def get_dataset_macro_analytics(
    filters: DatasetAnalyticsFilter,
) -> DatasetAnalyticsResponse:
    """Computes national agricultural trends and Pearson correlations from the preserved crop_yield.csv."""
    df = _load_raw_crop_yield_df().copy()

    if filters.crop:
        df = df[df["Crop"].str.lower() == filters.crop.strip().lower()]
    if filters.state:
        df = df[df["State"].str.lower() == filters.state.strip().lower()]
    if filters.season:
        df = df[df["Season"].str.lower() == filters.season.strip().lower()]
    if filters.year_start is not None:
        df = df[df["Crop_Year"] >= filters.year_start]
    if filters.year_end is not None:
        df = df[df["Crop_Year"] <= filters.year_end]

    if df.empty:
        return DatasetAnalyticsResponse(
            total_records=0,
            unique_crops=0,
            unique_states=0,
            avg_yield=0.0,
            avg_rainfall_mm=0.0,
            total_fertilizer_tonnes=0.0,
            total_pesticide_tonnes=0.0,
            crop_distribution=[],
            state_production=[],
            annual_trends=[],
            yield_comparison=[],
            correlation_matrix=[],
            source_mode="dataset_benchmark",
        )

    # Top crops distribution
    crop_grp = (
        df.groupby("Crop")
        .agg(records=("Yield", "count"), avg_yield=("Yield", "mean"))
        .sort_values(by="records", ascending=False)
        .head(10)
        .reset_index()
    )
    crop_dist = [
        CropDistributionItem(
            name=row["Crop"],
            records=int(row["records"]),
            avg_yield=round(float(row["avg_yield"]), 2),
        )
        for _, row in crop_grp.iterrows()
    ]

    # State production
    state_grp = (
        df.groupby("State")
        .agg(production_mt=("Production", "sum"), records=("Yield", "count"))
        .sort_values(by="production_mt", ascending=False)
        .head(8)
        .reset_index()
    )
    state_prod = [
        StateProductionItem(
            state=row["State"],
            production_mt=round(float(row["production_mt"]) / 1_000_000, 2),
            records=int(row["records"]),
        )
        for _, row in state_grp.iterrows()
    ]

    # Annual trends
    annual_grp = (
        df.groupby("Crop_Year")
        .agg(
            avg_rainfall=("Annual_Rainfall", "mean"),
            avg_yield=("Yield", "mean"),
            fert_sum=("Fertilizer", "sum"),
            pest_sum=("Pesticide", "sum"),
        )
        .reset_index()
        .sort_values(by="Crop_Year")
    )
    max_fert = float(annual_grp["fert_sum"].max()) or 1.0
    max_pest = float(annual_grp["pest_sum"].max()) or 1.0

    annual_trends = [
        AnnualTrendItem(
            year=int(row["Crop_Year"]),
            avg_rainfall=round(float(row["avg_rainfall"]), 1),
            avg_yield=round(float(row["avg_yield"]), 2),
            fertilizer_index=round(float(row["fert_sum"] / max_fert * 100), 1),
            pesticide_index=round(float(row["pest_sum"] / max_pest * 100), 1),
        )
        for _, row in annual_grp.iterrows()
    ]

    # Seasonal yield comparison
    top_crop_names = [c.name for c in crop_dist[:6]]
    yield_comp: list[YieldComparisonItem] = []
    for c_name in top_crop_names:
        c_sub = df[df["Crop"] == c_name]
        k_val = c_sub[c_sub["Season"].str.contains("Kharif", case=False)]["Yield"].mean()
        r_val = c_sub[c_sub["Season"].str.contains("Rabi", case=False)]["Yield"].mean()
        w_val = c_sub["Yield"].mean()
        yield_comp.append(
            YieldComparisonItem(
                crop=c_name,
                kharif=round(float(k_val) if pd.notna(k_val) else 0.0, 2),
                rabi=round(float(r_val) if pd.notna(r_val) else 0.0, 2),
                whole_year=round(float(w_val) if pd.notna(w_val) else 0.0, 2),
            )
        )

    # Correlation matrix across physical features (excluding target-leakage Production)
    numeric_cols = ["Area", "Annual_Rainfall", "Fertilizer", "Pesticide", "Yield"]
    valid_cols = [c for c in numeric_cols if c in df.columns]
    corr_df = df[valid_cols].corr()

    correlations: list[CorrelationItem] = []
    for col_x in valid_cols:
        for col_y in valid_cols:
            val = corr_df.loc[col_x, col_y]
            correlations.append(
                CorrelationItem(
                    feature_x=col_x,
                    feature_y=col_y,
                    correlation=round(float(val) if pd.notna(val) else 0.0, 3),
                )
            )

    return DatasetAnalyticsResponse(
        total_records=len(df),
        unique_crops=int(df["Crop"].nunique()),
        unique_states=int(df["State"].nunique()),
        avg_yield=round(float(df["Yield"].mean()), 2),
        avg_rainfall_mm=round(float(df["Annual_Rainfall"].mean()), 1),
        total_fertilizer_tonnes=round(float(df["Fertilizer"].sum() / 1000), 1),
        total_pesticide_tonnes=round(float(df["Pesticide"].sum() / 1000), 1),
        crop_distribution=crop_dist,
        state_production=state_prod,
        annual_trends=annual_trends,
        yield_comparison=yield_comp,
        correlation_matrix=correlations,
        source_mode="dataset_benchmark",
    )
