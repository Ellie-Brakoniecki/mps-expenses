"""Cleaning functions for IPSA expenses data."""

from __future__ import annotations

import logging
import re

import pandas as pd


LOGGER = logging.getLogger(__name__)

CANONICAL_COLUMN_ALIASES = {
    "mp's name": "mp_name",
    "mp_s_name": "mp_name",
    "previous constituency": "previous_constituency",
    "previous_constituency": "previous_constituency",
    "constituency since 5 july 2024": "constituency",
    "constituency_since_5_july_2024": "constituency",
    "constituency": "constituency",
    "office budget": "office_budget",
    "office_budget": "office_budget",
    "office maximum budget available": "office_budget",
    "office_maximum_budget_available": "office_budget",
    "reason for budget set": "office_budget_reason",
    "office spend": "office_spend",
    "office_spend": "office_spend",
    "subtotal of office running costs": "office_spend",
    "subtotal_of_office_running_costs": "office_spend",
    "remaining office budget": "remaining_office_budget",
    "remaining_office_budget": "remaining_office_budget",
    "staffing budget": "staffing_budget",
    "staffing_budget": "staffing_budget",
    "staffing maximum budget available": "staffing_budget",
    "staffing_maximum_budget_available": "staffing_budget",
    "reason for budget set_1": "staffing_budget_reason",
    "staffing spend": "staffing_spend",
    "staffing_spend": "staffing_spend",
    "remaining staffing budget": "remaining_staffing_budget",
    "remaining_staffing_budget": "remaining_staffing_budget",
    "winding_up budget": "winding_up_budget",
    "winding_up_budget": "winding_up_budget",
    "wind_up maximum budget available": "winding_up_budget",
    "wind_up_maximum_budget_available": "winding_up_budget",
    "reason for budget set_2": "winding_up_budget_reason",
    "winding_up spend": "winding_up_spend",
    "winding_up_spend": "winding_up_spend",
    "wind_up spend": "winding_up_spend",
    "wind_up_spend": "winding_up_spend",
    "remaining winding_up budget": "remaining_winding_up_budget",
    "remaining_winding_up_budget": "remaining_winding_up_budget",
    "remaining wind_up budget": "remaining_winding_up_budget",
    "remaining_wind_up_budget": "remaining_winding_up_budget",
    "accommodation budget": "accommodation_budget",
    "accommodation_budget": "accommodation_budget",
    "accommodation maximum budget available": "accommodation_budget",
    "accommodation_maximum_budget_available": "accommodation_budget",
    "reason for budget set_3": "accommodation_budget_reason",
    "accommodation spend": "accommodation_spend",
    "accommodation_spend": "accommodation_spend",
    "remaining accommodation budget": "remaining_accommodation_budget",
    "remaining_accommodation_budget": "remaining_accommodation_budget",
    "travel and subsistence (uncapped)": "travel_spend",
    "travel_and_subsistence_uncapped": "travel_spend",
    "travel and subsistence spend": "travel_spend",
    "travel_and_subsistence_spend": "travel_spend",
    "travel and subsistence maximum budget available": "travel_budget",
    "travel_and_subsistence_maximum_budget_available": "travel_budget",
    "other costs (uncapped)": "other_costs_spend",
    "other_costs_uncapped": "other_costs_spend",
    "other costs spend": "other_costs_spend",
    "other_costs_spend": "other_costs_spend",
    "other costs maximum budget available": "other_costs_budget",
    "other_costs_maximum_budget_available": "other_costs_budget",
    "subtotal of other parliamentary costs": "other_parliamentary_costs_spend",
    "subtotal_of_other_parliamentary_costs": "other_parliamentary_costs_spend",
    "overall total spend for this financial year": "overall_total_spend",
    "overall_total_spend_for_this_financial_year": "overall_total_spend",
    "start_up maximum budget available": "startup_budget",
    "start_up_maximum_budget_available": "startup_budget",
    "start_up spend": "startup_spend",
    "start_up_spend": "startup_spend",
    "remaining start_up budget": "remaining_startup_budget",
    "remaining_start_up_budget": "remaining_startup_budget",
    "reason for budget set_4": "startup_budget_reason",
    "pid": "mp_id",
    "source_url": "source_url",
    "source_file": "source_file",
}

MONETARY_COLUMNS = [
    "office_budget",
    "office_spend",
    "remaining_office_budget",
    "staffing_budget",
    "staffing_spend",
    "remaining_staffing_budget",
    "winding_up_budget",
    "winding_up_spend",
    "remaining_winding_up_budget",
    "accommodation_budget",
    "accommodation_spend",
    "remaining_accommodation_budget",
    "travel_budget",
    "travel_spend",
    "other_costs_budget",
    "other_costs_spend",
    "other_parliamentary_costs_spend",
    "overall_total_spend",
    "startup_budget",
    "startup_spend",
    "remaining_startup_budget",
]


def clean_currency_value(value):
    """Convert a raw currency-like value into a numeric form."""
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return pd.NA
    if text.lower() == "uncapped":
        return pd.NA

    negative = text.startswith("(") and text.endswith(")") or text.startswith("-")
    match = re.search(r"-?£?[0-9,]+(?:\.[0-9]+)?", text)
    if not match:
        LOGGER.warning("Unable to parse currency value: %s", value)
        return pd.NA

    cleaned = match.group(0).replace("£", "").replace(",", "").strip()

    try:
        numeric_value = abs(float(cleaned))
    except ValueError:
        LOGGER.warning("Unable to parse currency value: %s", value)
        return pd.NA

    return -numeric_value if negative else numeric_value


def standardise_columns(df):
    """Standardise incoming column names to a consistent schema."""
    LOGGER.info("Standardising IPSA raw columns")
    renamed_columns = [_canonicalise_column_name(column) for column in df.columns]

    renamed = df.copy()
    renamed.columns = renamed_columns

    standardised = pd.DataFrame(index=renamed.index)
    for column_name in pd.Index(renamed.columns).unique():
        matching = renamed.loc[:, renamed.columns == column_name]
        if isinstance(matching, pd.Series):
            standardised[column_name] = matching
        else:
            standardised[column_name] = matching.bfill(axis=1).iloc[:, 0]

    if "constituency" in standardised.columns and "previous_constituency" in standardised.columns:
        standardised["constituency"] = standardised["constituency"].fillna(standardised["previous_constituency"])

    return standardised


def clean_expenses_data(df):
    """Apply the end-to-end cleaning pipeline to raw IPSA expenses data."""
    LOGGER.info("Cleaning IPSA expenses dataset with %s rows", len(df))
    cleaned = standardise_columns(df)

    for column in MONETARY_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].map(clean_currency_value).astype("Float64")

    cleaned["mp_name"] = cleaned.get("mp_name", pd.Series(index=cleaned.index, dtype="object")).astype("string").str.strip()
    cleaned["constituency"] = cleaned.get("constituency", pd.Series(index=cleaned.index, dtype="object")).astype("string").str.strip()
    cleaned["financial_year"] = _derive_financial_year(cleaned)
    cleaned["record_id"] = cleaned["financial_year"].fillna("unknown") + "::" + cleaned["mp_name"].fillna("unknown")

    _fill_remaining_budget(cleaned, "office")
    _fill_remaining_budget(cleaned, "staffing")
    _fill_remaining_budget(cleaned, "winding_up")
    _fill_remaining_budget(cleaned, "accommodation")
    _fill_remaining_budget(cleaned, "startup")

    spend_columns = [
        column
        for column in [
            "office_spend",
            "staffing_spend",
            "winding_up_spend",
            "accommodation_spend",
            "travel_spend",
            "other_costs_spend",
            "startup_spend",
        ]
        if column in cleaned.columns
    ]
    budget_columns = [
        column
        for column in [
            "office_budget",
            "staffing_budget",
            "winding_up_budget",
            "accommodation_budget",
            "travel_budget",
            "other_costs_budget",
            "startup_budget",
        ]
        if column in cleaned.columns
    ]
    remaining_columns = [
        column
        for column in [
            "remaining_office_budget",
            "remaining_staffing_budget",
            "remaining_winding_up_budget",
            "remaining_accommodation_budget",
            "remaining_startup_budget",
        ]
        if column in cleaned.columns
    ]

    cleaned["total_spend"] = cleaned.get("overall_total_spend")
    if spend_columns:
        calculated_spend = cleaned[spend_columns].sum(axis=1, min_count=1).astype("Float64")
        cleaned["total_spend"] = cleaned["total_spend"].fillna(calculated_spend)

    cleaned["total_budget"] = cleaned[budget_columns].sum(axis=1, min_count=1).astype("Float64") if budget_columns else pd.Series(pd.NA, index=cleaned.index, dtype="Float64")
    cleaned["total_remaining_budget"] = cleaned[remaining_columns].sum(axis=1, min_count=1).astype("Float64") if remaining_columns else pd.Series(pd.NA, index=cleaned.index, dtype="Float64")
    cleaned["uncapped_spend_total"] = cleaned[[column for column in ["travel_spend", "other_costs_spend"] if column in cleaned.columns]].sum(axis=1, min_count=1).astype("Float64")
    cleaned["has_accommodation_budget"] = cleaned.get("accommodation_budget", pd.Series(0, index=cleaned.index)).fillna(0).gt(0)
    cleaned["has_startup_budget"] = cleaned.get("startup_budget", pd.Series(0, index=cleaned.index)).fillna(0).gt(0) | cleaned.get("startup_spend", pd.Series(0, index=cleaned.index)).fillna(0).gt(0)

    reason_text = cleaned.filter(regex=r"_budget_reason$").fillna("").astype("string").agg(" ".join, axis=1).str.lower()
    cleaned["is_london_group"] = reason_text.str.contains("london", na=False)

    LOGGER.info("Completed cleaning. Dataset now has %s columns", len(cleaned.columns))
    return cleaned


def _canonicalise_column_name(column_name: str) -> str:
    normalised = str(column_name).replace("\ufeff", "").strip().lower()
    normalised = re.sub(r"[\.-]", "_", normalised)
    normalised = re.sub(r"[^a-z0-9]+", "_", normalised).strip("_")
    return CANONICAL_COLUMN_ALIASES.get(normalised, CANONICAL_COLUMN_ALIASES.get(normalised.replace("_", " "), normalised))


def _fill_remaining_budget(df: pd.DataFrame, prefix: str) -> None:
    budget_column = f"{prefix}_budget"
    spend_column = f"{prefix}_spend"
    remaining_column = f"remaining_{prefix}_budget"

    if budget_column not in df.columns or spend_column not in df.columns:
        return

    if remaining_column not in df.columns:
        df[remaining_column] = pd.Series(pd.NA, index=df.index, dtype="Float64")


def _derive_financial_year(df: pd.DataFrame) -> pd.Series:
    source_url_year = df.get("source_url", pd.Series(pd.NA, index=df.index, dtype="string")).astype("string").str.extract(
        r"year=([0-9]{2}_[0-9]{2})",
        expand=False,
    )
    source_file_year = df.get("source_file", pd.Series(pd.NA, index=df.index, dtype="string")).astype("string").str.extract(
        r"([0-9]{2}_[0-9]{2})",
        expand=False,
    )
    existing_year = df.get("financial_year", pd.Series(pd.NA, index=df.index, dtype="string")).astype("string")
    return existing_year.fillna(source_url_year).fillna(source_file_year)

    computed_remaining = df[budget_column] - df[spend_column]
    df[remaining_column] = df[remaining_column].fillna(computed_remaining)