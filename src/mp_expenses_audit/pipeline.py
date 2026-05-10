"""Top-level pipeline entry points for the MP expenses audit workflow."""

from __future__ import annotations

import logging
from pathlib import Path

from mp_expenses_audit import config
from mp_expenses_audit.analytics.features import engineer_features
from mp_expenses_audit.analytics.risk_flags import apply_risk_flags, assign_risk_priority
from mp_expenses_audit.data_quality.cleaning import clean_expenses_data
from mp_expenses_audit.data_quality.validation import build_limitations_summary, run_validation_checks
from mp_expenses_audit.ingestion.annual_publications import run_ingestion_pipeline
from mp_expenses_audit.reporting.dashboard_data import build_dashboard_dataset
from mp_expenses_audit.utils.logging_utils import configure_logging


LOGGER = logging.getLogger(__name__)


def run_pipeline() -> dict[str, Path]:
    """Run the end-to-end audit pipeline from ingestion to dashboard-ready outputs."""
    configure_logging()
    _ensure_output_directories()

    LOGGER.info("Running MP expenses audit pipeline")
    raw_df = run_ingestion_pipeline()
    clean_df = clean_expenses_data(raw_df)
    validation_report = run_validation_checks(clean_df)
    limitations_summary = build_limitations_summary()
    feature_df = engineer_features(clean_df)
    risk_df = assign_risk_priority(apply_risk_flags(feature_df))
    dashboard_df = build_dashboard_dataset(risk_df)

    outputs = {
        "ingested_data": _save_dataframe(raw_df, config.INTERIM_DATA_DIR / "ingested_total_spend.csv"),
        "cleaned_data": _save_dataframe(clean_df, config.INTERIM_DATA_DIR / "cleaned_total_spend.csv"),
        "validation_report": _save_dataframe(validation_report, config.VALIDATION_OUTPUT_DIR / "validation_report.csv"),
        "limitations_summary": _save_dataframe(limitations_summary, config.VALIDATION_OUTPUT_DIR / "limitations_summary.csv"),
        "analytics_dataset": _save_dataframe(risk_df, config.PROCESSED_DATA_DIR / "mp_expenses_audit_dataset.csv"),
        "risk_output": _save_dataframe(risk_df, config.ANALYTICS_OUTPUT_DIR / "risk_priorities.csv"),
        "dashboard_dataset": _save_dataframe(dashboard_df, config.PROCESSED_DATA_DIR / "dashboard_dataset.csv"),
        "dashboard_output": _save_dataframe(dashboard_df, config.DASHBOARD_OUTPUT_DIR / "dashboard_dataset.csv"),
    }
    LOGGER.info("Pipeline completed successfully")
    return outputs


def _ensure_output_directories() -> None:
    directories = [
        config.INTERIM_DATA_DIR,
        config.PROCESSED_DATA_DIR,
        config.VALIDATION_OUTPUT_DIR,
        config.ANALYTICS_OUTPUT_DIR,
        config.DASHBOARD_OUTPUT_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def _save_dataframe(df, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path