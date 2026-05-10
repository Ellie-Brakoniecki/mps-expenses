"""Basic scaffold checks for the initial project structure."""

from mp_expenses_audit import config


def test_audit_thresholds_are_defined() -> None:
    assert "high_utilisation_pct" in config.AUDIT_THRESHOLDS
    assert "z_score_cutoff" in config.AUDIT_THRESHOLDS