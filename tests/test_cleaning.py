from mp_expenses_audit.data_quality.cleaning import clean_currency_value, clean_expenses_data


def test_clean_currency_value_handles_annotations() -> None:
    value = "-£577.49\n(MP has agreed to offset this by reducing spend in the 2014-15 budget)"
    assert clean_currency_value(value) == -577.49


def test_clean_expenses_data_standardises_mp_name() -> None:
    raw_rows = {
        "\ufeff\ufeffMP's name": ["Example MP"],
        "Constituency": ["Example Seat"],
        "Office maximum budget available": ["£1,000.00"],
        "Subtotal of office running costs": ["£250.00"],
        "source_url": ["https://www.theipsa.org.uk/api/download?type=totalSpend&year=24_25"],
        "source_file": ["data/raw/example.csv"],
    }

    clean_df = clean_expenses_data(__import__("pandas").DataFrame(raw_rows))

    assert clean_df.loc[0, "mp_name"] == "Example MP"
    assert clean_df.loc[0, "financial_year"] == "24_25"
    assert clean_df.loc[0, "office_budget"] == 1000.0
    assert clean_df.loc[0, "office_spend"] == 250.0