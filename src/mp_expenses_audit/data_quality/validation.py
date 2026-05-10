"""Validation functions for audit-ready data QA."""

from __future__ import annotations

import logging

import pandas as pd

from mp_expenses_audit import config


LOGGER = logging.getLogger(__name__)


def run_validation_checks(df):
    """Run structural and quality checks against a cleaned dataset."""
    LOGGER.info("Running validation checks across %s rows", len(df))
    validation_rows: list[dict[str, object]] = []

    for column in config.REQUIRED_COLUMNS:
        is_present = column in df.columns
        validation_rows.append(
            {
                "check_type": "required_column",
                "check_name": f"required_{column}",
                "column_name": column,
                "issue_count": 0 if is_present else 1,
                "issue_pct": 0.0 if is_present else 100.0,
                "status": "pass" if is_present else "fail",
                "details": "Required column present" if is_present else "Required column missing",
            }
        )

    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        validation_rows.append(
            {
                "check_type": "missing_values",
                "check_name": f"missing_{column}",
                "column_name": column,
                "issue_count": missing_count,
                "issue_pct": round((missing_count / len(df) * 100), 2) if len(df) else 0.0,
                "status": "pass" if missing_count == 0 else "review",
                "details": "Missing value summary",
            }
        )

    monetary_columns = [column for column in df.columns if column.endswith("_budget") or column.endswith("_spend") or column.endswith("_remaining_budget") or column in {"total_spend", "total_budget", "total_remaining_budget", "uncapped_spend_total"}]
    for column in monetary_columns:
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        negative_count = int(numeric_series.fillna(0).lt(0).sum())
        validation_rows.append(
            {
                "check_type": "negative_values",
                "check_name": f"negative_{column}",
                "column_name": column,
                "issue_count": negative_count,
                "issue_pct": round((negative_count / len(df) * 100), 2) if len(df) else 0.0,
                "status": "pass" if negative_count == 0 else "review",
                "details": "Negative monetary values should be reviewed",
            }
        )

    duplicate_keys = [column for column in ["mp_name", "financial_year"] if column in df.columns]
    duplicate_count = int(df.duplicated(subset=duplicate_keys).sum()) if len(duplicate_keys) == 2 else 0
    validation_rows.append(
        {
            "check_type": "duplicates",
            "check_name": "duplicate_mp_year_records",
            "column_name": "mp_name,financial_year",
            "issue_count": duplicate_count,
            "issue_pct": round((duplicate_count / len(df) * 100), 2) if len(df) else 0.0,
            "status": "pass" if duplicate_count == 0 else "review",
            "details": "Duplicate MP and financial year records",
        }
    )

    for prefix in ["office", "staffing", "winding_up", "accommodation", "startup"]:
        budget_column = f"{prefix}_budget"
        spend_column = f"{prefix}_spend"
        if budget_column in df.columns and spend_column in df.columns:
            budget_series = pd.to_numeric(df[budget_column], errors="coerce")
            spend_series = pd.to_numeric(df[spend_column], errors="coerce")
            ratio = (spend_series / budget_series) * 100
            invalid_count = int(ratio[(df[budget_column] > 0) & ((ratio < 0) | (ratio > 150))].count())
            validation_rows.append(
                {
                    "check_type": "range_logic",
                    "check_name": f"utilisation_bounds_{prefix}",
                    "column_name": prefix,
                    "issue_count": invalid_count,
                    "issue_pct": round((invalid_count / len(df) * 100), 2) if len(df) else 0.0,
                    "status": "pass" if invalid_count == 0 else "review",
                    "details": "Utilisation outside expected logical range 0-150%",
                }
            )

    report = pd.DataFrame(validation_rows)
    LOGGER.info("Validation generated %s rows", len(report))
    return report


def build_limitations_summary():
    """Create a structured summary of data limitations and assumptions."""
    return pd.DataFrame(
        [
            {
                "category": "data_limitation",
                "item": "aggregated_data",
                "description": "IPSA annual publications are aggregated summaries and do not include full transactional context.",
            },
            {
                "category": "data_limitation",
                "item": "limited_context",
                "description": "Important contextual factors such as constituency workload and local operating conditions are not present.",
            },
            {
                "category": "data_limitation",
                "item": "schema_variation",
                "description": "Column names vary across publication years and require standardisation before comparison.",
            },
            {
                "category": "assumption",
                "item": "currency_cleaning",
                "description": "Currency symbols, commas, empty strings, and N/A values are converted into numeric values or missing values without altering underlying meaning.",
            },
            {
                "category": "assumption",
                "item": "remaining_budget_derivation",
                "description": "Missing remaining budget fields are derived as budget minus spend where both inputs are available.",
            },
            {
                "category": "assumption",
                "item": "total_spend_derivation",
                "description": "Total spend is taken from the IPSA overall total where available, otherwise it is derived from component spend categories.",
            },
        ]
    )