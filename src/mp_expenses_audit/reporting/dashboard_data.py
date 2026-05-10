"""Reporting module for dashboard-ready audit outputs."""

from __future__ import annotations

import logging


LOGGER = logging.getLogger(__name__)


def build_dashboard_dataset(df):
    """Prepare a prioritisation-first dataset for dashboard consumption."""
    LOGGER.info("Preparing dashboard dataset from %s rows", len(df))
    dashboard_df = df.copy()
    dashboard_df = dashboard_df.sort_values(
        by=["risk_priority_rank", "risk_flag_count", "total_spend"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    dashboard_df["review_rank"] = dashboard_df.index + 1
    dashboard_df["review_summary"] = dashboard_df["risk_priority"] + " priority | " + dashboard_df["risk_flag_count"].astype(str) + " flags"

    columns = [
        "review_rank",
        "mp_name",
        "constituency",
        "financial_year",
        "peer_group",
        "risk_priority",
        "risk_flag_count",
        "overall_utilisation_pct",
        "total_spend",
        "uncapped_spend_total",
        "travel_spend",
        "risk_explanations",
        "review_summary",
    ]
    available_columns = [column for column in columns if column in dashboard_df.columns]
    return dashboard_df[available_columns]