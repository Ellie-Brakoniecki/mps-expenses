# Limitations and Assumptions

This document sets out the main limitations and assumptions in the MP expenses audit analytics project.

It is intended to be read alongside the validation outputs in `outputs/validation/`.

## Purpose

The analysis is designed to support audit prioritisation.

It highlights notable patterns that may be worthy of further review. It does not make allegations and it does not replace auditor judgement.

## Main Limitations

### 1. Aggregated source data

The IPSA annual publications are aggregated summaries.

This means the dataset does not contain full transaction-level detail. As a result, the analysis can show broad spending patterns, but it cannot explain every individual item behind those totals.

### 2. Limited contextual information

The source data does not include all factors that may affect spending.

Examples include:

- constituency workload
- local operating conditions
- office structure
- individual circumstances that may affect claims or budget use

This means a notable pattern in the data may still have a reasonable explanation outside the dataset.

### 3. Variation in source file structure

Column names and layouts vary across publication years.

Because of this, the data has to be standardised before years can be compared in a consistent way.

### 4. Outputs are indicators, not conclusions

Risk flags and review priorities are designed as indicators for audit follow-up.

They show where there may be notable variance relative to thresholds or peer groups. They do not show wrongdoing, intent, or error on their own.

## Main Assumptions

### 1. Currency values are cleaned into numeric form

Currency symbols, commas, empty strings, and `N/A` values are converted into numeric values or missing values.

This is done so the data can be analysed consistently without changing the underlying meaning of the source fields.

### 2. Missing remaining budget values may be derived

Where a remaining budget field is missing, it may be derived as:

`budget - spend`

This is only done where both the budget and spend values are available.

### 3. Total spend may be derived when needed

Where IPSA provides an overall total spend field, that value is used.

If it is not available, total spend is derived from the relevant spend components in the cleaned dataset.

### 4. Financial year is derived during cleaning

The combined raw dataset does not contain a standard `financial_year` column.

That field is created during cleaning from source metadata so records can be grouped and compared consistently across years.

### 5. Peer groups are simplified

Peer comparison is based on a practical grouping approach rather than a complete model of all relevant factors.

This improves fairness compared with comparing all MPs together, but it does not remove the need for judgement.

## Practical Interpretation

When using the outputs, the safest interpretation is:

- this analysis supports prioritisation
- it identifies notable patterns
- it helps decide where review effort may add value
- final conclusions should always depend on human review

## Related Files

- `outputs/validation/validation_report.csv`
- `outputs/validation/limitations_summary.csv`
- `data/interim/cleaned_total_spend.csv`
- `data/processed/mp_expenses_audit_dataset.csv`