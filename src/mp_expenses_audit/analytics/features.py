"""Feature engineering module for audit analytics."""

from __future__ import annotations

import logging

import pandas as pd


LOGGER = logging.getLogger(__name__)


def build_peer_groups(df):
    """Assign records to peer groups for fair comparison."""
    peer_grouped = df.copy()
    peer_grouped["mp_status_group"] = peer_grouped["has_startup_budget"].map({True: "new_mp", False: "returning_mp"})
    peer_grouped["accommodation_group"] = peer_grouped["has_accommodation_budget"].map({True: "with_accommodation", False: "without_accommodation"})
    peer_grouped["location_group"] = peer_grouped["is_london_group"].map({True: "london", False: "non_london"})
    peer_grouped["peer_group"] = (
        peer_grouped["mp_status_group"]
        + "|"
        + peer_grouped["location_group"]
        + "|"
        + peer_grouped["accommodation_group"]
    )
    return peer_grouped


def engineer_features(df):
    """Create audit-relevant spend and utilisation metrics."""
    LOGGER.info("Engineering audit features for %s rows", len(df))
    featured = build_peer_groups(df)

    _add_utilisation(featured, "office")
    _add_utilisation(featured, "staffing")
    _add_utilisation(featured, "winding_up")
    _add_utilisation(featured, "accommodation")
    _add_utilisation(featured, "startup")

    featured["overall_utilisation_pct"] = _safe_percentage(featured["total_spend"], featured["total_budget"])
    featured["travel_spend_share_pct"] = _safe_percentage(featured.get("travel_spend"), featured["total_spend"])
    featured["uncapped_spend_share_pct"] = _safe_percentage(featured["uncapped_spend_total"], featured["total_spend"])

    featured["total_spend_peer_percentile"] = featured.groupby("peer_group")["total_spend"].rank(pct=True, method="average")
    featured["travel_spend_peer_percentile"] = featured.groupby("peer_group")["travel_spend"].rank(pct=True, method="average")
    featured["uncapped_spend_peer_percentile"] = featured.groupby("peer_group")["uncapped_spend_total"].rank(pct=True, method="average")

    for metric in ["total_spend", "overall_utilisation_pct", "travel_spend", "uncapped_spend_total", "accommodation_spend"]:
        featured[f"{metric}_zscore"] = featured.groupby("peer_group")[metric].transform(_group_zscore).astype("Float64")

    LOGGER.info("Feature engineering completed")
    return featured


def _add_utilisation(df: pd.DataFrame, prefix: str) -> None:
    budget_column = f"{prefix}_budget"
    spend_column = f"{prefix}_spend"
    if budget_column not in df.columns or spend_column not in df.columns:
        df[f"{prefix}_utilisation_pct"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        return

    df[f"{prefix}_utilisation_pct"] = _safe_percentage(df[spend_column], df[budget_column])


def _safe_percentage(numerator: pd.Series | None, denominator: pd.Series | None) -> pd.Series:
    if numerator is None or denominator is None:
        return pd.Series(pd.NA, dtype="Float64")

    numerator_series = pd.to_numeric(numerator, errors="coerce")
    denominator_series = pd.to_numeric(denominator, errors="coerce")
    result = (numerator_series / denominator_series.where(denominator_series > 0)) * 100
    return result.astype("Float64")


def _group_zscore(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    std = numeric.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(0, index=series.index, dtype="Float64")
    return ((numeric - numeric.mean()) / std).astype("Float64")