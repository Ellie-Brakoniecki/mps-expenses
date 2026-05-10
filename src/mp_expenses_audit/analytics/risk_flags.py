"""Risk flagging module for explainable prioritisation outputs."""

from __future__ import annotations

import logging

import pandas as pd

from mp_expenses_audit import config


LOGGER = logging.getLogger(__name__)

FLAG_COLUMNS = [
    "high_overall_utilisation_flag",
    "low_staffing_utilisation_flag",
    "high_travel_spend_flag",
    "high_uncapped_spend_flag",
    "accommodation_outlier_flag",
    "high_total_spend_flag",
]


def apply_risk_flags(df):
    """Apply config-driven indicators to identify records worthy of review."""
    LOGGER.info("Applying risk flags to %s rows", len(df))
    flagged = df.copy()
    thresholds = config.AUDIT_THRESHOLDS

    flagged["high_overall_utilisation_flag"] = flagged["overall_utilisation_pct"].ge(thresholds["high_utilisation_pct"])
    flagged["low_staffing_utilisation_flag"] = flagged["staffing_utilisation_pct"].le(thresholds["low_staffing_utilisation_pct"]) & flagged["staffing_budget"].gt(0)
    flagged["high_travel_spend_flag"] = flagged["travel_spend_peer_percentile"].ge(thresholds["high_travel_spend_percentile"]) | flagged["travel_spend_zscore"].ge(thresholds["z_score_cutoff"])
    flagged["high_uncapped_spend_flag"] = flagged["uncapped_spend_peer_percentile"].ge(thresholds["high_uncapped_spend_percentile"]) | flagged["uncapped_spend_total_zscore"].ge(thresholds["z_score_cutoff"])
    flagged["accommodation_outlier_flag"] = flagged["has_accommodation_budget"] & flagged["accommodation_spend_zscore"].ge(thresholds["z_score_cutoff"])
    flagged["high_total_spend_flag"] = flagged["total_spend_peer_percentile"].ge(0.95) & flagged["total_spend"].ge(thresholds["material_spend_threshold_gbp"])

    for column in FLAG_COLUMNS:
        flagged[column] = flagged[column].fillna(False).astype(bool)

    flagged["risk_flag_count"] = flagged[FLAG_COLUMNS].sum(axis=1)
    flagged["risk_explanations"] = flagged.apply(_build_explanations, axis=1)
    return flagged


def assign_risk_priority(df):
    """Aggregate indicators into a simple audit review priority."""
    prioritised = df.copy()
    high_threshold = config.AUDIT_THRESHOLDS["high_risk_flag_count"]
    prioritised["risk_priority"] = "Low"
    prioritised.loc[prioritised["risk_flag_count"] >= 2, "risk_priority"] = "Medium"
    prioritised.loc[prioritised["risk_flag_count"] >= high_threshold, "risk_priority"] = "High"
    prioritised["risk_priority_rank"] = prioritised["risk_priority"].map({"High": 3, "Medium": 2, "Low": 1}).astype(int)
    return prioritised


def _build_explanations(row: pd.Series) -> str:
    explanations: list[str] = []
    if bool(row.get("high_overall_utilisation_flag", False)):
        explanations.append(f"Overall utilisation of {row.get('overall_utilisation_pct', 0):.1f}% is above the audit threshold.")
    if bool(row.get("low_staffing_utilisation_flag", False)):
        explanations.append(f"Staffing utilisation of {row.get('staffing_utilisation_pct', 0):.1f}% is materially below the peer benchmark threshold.")
    if bool(row.get("high_travel_spend_flag", False)):
        explanations.append("Travel spend is in the highest peer-group range and may be worthy of further review.")
    if bool(row.get("high_uncapped_spend_flag", False)):
        explanations.append("Uncapped spend is elevated relative to the peer group.")
    if bool(row.get("accommodation_outlier_flag", False)):
        explanations.append("Accommodation spend is a notable variance within the peer group.")
    if bool(row.get("high_total_spend_flag", False)):
        explanations.append("Overall spend is at the upper end of the peer-group distribution.")
    return " ".join(explanations) if explanations else "No notable variance flags were triggered for this record."