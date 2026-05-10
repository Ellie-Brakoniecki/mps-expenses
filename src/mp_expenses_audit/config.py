"""Central configuration for audit analytics thresholds and paths."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
VALIDATION_OUTPUT_DIR = OUTPUTS_DIR / "validation"
ANALYTICS_OUTPUT_DIR = OUTPUTS_DIR / "analytics"
DASHBOARD_OUTPUT_DIR = OUTPUTS_DIR / "dashboard"


AUDIT_THRESHOLDS = {
    "high_utilisation_pct": 95.0,
    "low_staffing_utilisation_pct": 40.0,
    "material_spend_threshold_gbp": 10000.0,
    "z_score_cutoff": 2.0,
    "high_travel_spend_percentile": 0.95,
    "high_uncapped_spend_percentile": 0.95,
    "high_risk_flag_count": 3,
}


REQUIRED_COLUMNS = [
    "mp_name",
    "constituency",
    "financial_year",
    "source_url",
    "source_file",
    "total_spend",
]