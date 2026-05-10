import pandas as pd

from mp_expenses_audit.analytics.risk_flags import apply_risk_flags, assign_risk_priority


def test_assign_risk_priority_sets_high_for_multiple_flags() -> None:
    df = pd.DataFrame(
        {
            "overall_utilisation_pct": [99.0],
            "staffing_utilisation_pct": [30.0],
            "staffing_budget": [100.0],
            "travel_spend_peer_percentile": [0.99],
            "travel_spend_zscore": [3.0],
            "uncapped_spend_peer_percentile": [0.99],
            "uncapped_spend_total_zscore": [3.0],
            "has_accommodation_budget": [True],
            "accommodation_spend_zscore": [3.0],
            "total_spend_peer_percentile": [0.99],
            "total_spend": [50000.0],
        }
    )

    flagged = apply_risk_flags(df)
    prioritised = assign_risk_priority(flagged)

    assert prioritised.loc[0, "risk_priority"] == "High"
    assert prioritised.loc[0, "risk_flag_count"] >= 3